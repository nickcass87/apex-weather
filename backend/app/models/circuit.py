from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import String, Float, Integer, Text, ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Circuit(Base):
    __tablename__ = "circuits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    length_km: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    timezone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    altitude_m: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Comma-separated series: "F1,WEC,GT3"
    series: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Sector count for future sector-level weather
    sector_count: Mapped[int] = mapped_column(Integer, default=3)
    # Surface type affects track temperature model
    surface_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True, default="standard_asphalt")
