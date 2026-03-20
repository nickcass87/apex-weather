from __future__ import annotations

from typing import Optional

from pydantic import BaseModel
from uuid import UUID


class CircuitBase(BaseModel):
    name: str
    country: str
    latitude: float
    longitude: float
    length_km: Optional[float] = None
    timezone: Optional[str] = None
    altitude_m: Optional[int] = None
    series: Optional[str] = None
    sector_count: int = 3
    surface_type: Optional[str] = "standard_asphalt"


class CircuitOut(CircuitBase):
    id: UUID

    model_config = {"from_attributes": True}
