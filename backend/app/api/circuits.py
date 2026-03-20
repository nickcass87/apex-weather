from __future__ import annotations

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.circuit import Circuit
from app.schemas.circuit import CircuitOut

router = APIRouter(prefix="/circuits", tags=["circuits"])


@router.get("/", response_model=List[CircuitOut])
def list_circuits(
    country: Optional[str] = None,
    series: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Circuit)
    if country:
        query = query.filter(Circuit.country.ilike(f"%{country}%"))
    if series:
        query = query.filter(Circuit.series.ilike(f"%{series}%"))
    return query.order_by(Circuit.name).all()


@router.get("/{circuit_id}", response_model=CircuitOut)
def get_circuit(circuit_id: str, db: Session = Depends(get_db)):
    circuit = db.query(Circuit).filter(Circuit.id == circuit_id).first()
    if not circuit:
        raise HTTPException(status_code=404, detail="Circuit not found")
    return circuit
