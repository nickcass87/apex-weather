"""Race weekend session timeline API.

Provides session scheduling and weather windows for race weekends.
"""
from __future__ import annotations

from typing import Optional, List
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.models.circuit import Circuit

router = APIRouter(prefix="/sessions", tags=["sessions"])


class SessionSchedule(BaseModel):
    name: str
    session_type: str  # practice, qualifying, sprint, race
    start_time: datetime
    end_time: datetime
    duration_minutes: int


class RaceWeekendResponse(BaseModel):
    circuit_id: str
    circuit_name: str
    timezone: Optional[str] = None
    sessions: List[SessionSchedule] = []


# Standard race weekend templates
WEEKEND_TEMPLATES = {
    "f1_standard": [
        {"name": "Free Practice 1", "session_type": "practice", "day_offset": 0, "hour": 13, "duration": 60},
        {"name": "Free Practice 2", "session_type": "practice", "day_offset": 0, "hour": 17, "duration": 60},
        {"name": "Free Practice 3", "session_type": "practice", "day_offset": 1, "hour": 12, "duration": 60},
        {"name": "Qualifying", "session_type": "qualifying", "day_offset": 1, "hour": 16, "duration": 60},
        {"name": "Race", "session_type": "race", "day_offset": 2, "hour": 15, "duration": 120},
    ],
    "f1_sprint": [
        {"name": "Free Practice 1", "session_type": "practice", "day_offset": 0, "hour": 13, "duration": 60},
        {"name": "Sprint Qualifying", "session_type": "qualifying", "day_offset": 0, "hour": 17, "duration": 45},
        {"name": "Sprint Race", "session_type": "sprint", "day_offset": 1, "hour": 12, "duration": 30},
        {"name": "Qualifying", "session_type": "qualifying", "day_offset": 1, "hour": 16, "duration": 60},
        {"name": "Race", "session_type": "race", "day_offset": 2, "hour": 15, "duration": 120},
    ],
    "wec_standard": [
        {"name": "Free Practice 1", "session_type": "practice", "day_offset": 0, "hour": 10, "duration": 90},
        {"name": "Free Practice 2", "session_type": "practice", "day_offset": 0, "hour": 15, "duration": 90},
        {"name": "Free Practice 3", "session_type": "practice", "day_offset": 1, "hour": 10, "duration": 60},
        {"name": "Qualifying / Hyperpole", "session_type": "qualifying", "day_offset": 1, "hour": 14, "duration": 45},
        {"name": "Race", "session_type": "race", "day_offset": 2, "hour": 14, "duration": 360},
    ],
    "gt3_standard": [
        {"name": "Free Practice 1", "session_type": "practice", "day_offset": 0, "hour": 10, "duration": 60},
        {"name": "Free Practice 2", "session_type": "practice", "day_offset": 0, "hour": 14, "duration": 60},
        {"name": "Qualifying", "session_type": "qualifying", "day_offset": 1, "hour": 10, "duration": 30},
        {"name": "Race 1", "session_type": "race", "day_offset": 1, "hour": 14, "duration": 60},
        {"name": "Race 2", "session_type": "race", "day_offset": 2, "hour": 11, "duration": 60},
    ],
    "supercars_standard": [
        {"name": "Practice 1", "session_type": "practice", "day_offset": 0, "hour": 10, "duration": 45},
        {"name": "Practice 2", "session_type": "practice", "day_offset": 0, "hour": 14, "duration": 45},
        {"name": "Qualifying", "session_type": "qualifying", "day_offset": 1, "hour": 11, "duration": 30},
        {"name": "Race 1", "session_type": "race", "day_offset": 1, "hour": 14, "duration": 45},
        {"name": "Race 2", "session_type": "race", "day_offset": 2, "hour": 13, "duration": 45},
    ],
}


def _determine_series_template(series: Optional[str]) -> str:
    """Determine which weekend template to use based on circuit series."""
    if not series:
        return "f1_standard"
    s = series.lower()
    if "f1" in s:
        return "f1_standard"
    elif "wec" in s:
        return "wec_standard"
    elif "supercars" in s:
        return "supercars_standard"
    elif "gt3" in s or "dtm" in s:
        return "gt3_standard"
    return "f1_standard"


@router.get("/{circuit_id}", response_model=RaceWeekendResponse)
def get_race_weekend(
    circuit_id: str,
    template: Optional[str] = None,
    start_date: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Get a race weekend schedule for a circuit.

    If no start_date is provided, generates for this Friday-Sunday.
    If no template is provided, auto-detects from circuit series.
    """
    circuit = db.query(Circuit).filter(Circuit.id == circuit_id).first()
    if not circuit:
        raise HTTPException(status_code=404, detail="Circuit not found")

    # Determine template
    tmpl_name = template or _determine_series_template(circuit.series)
    tmpl = WEEKEND_TEMPLATES.get(tmpl_name, WEEKEND_TEMPLATES["f1_standard"])

    # Parse or default start date (next Friday)
    if start_date:
        try:
            base = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        now = datetime.now(timezone.utc)
        days_until_friday = (4 - now.weekday()) % 7
        if days_until_friday == 0 and now.hour > 12:
            days_until_friday = 7
        base = (now + timedelta(days=days_until_friday)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

    sessions = []
    for s in tmpl:
        start = base + timedelta(days=s["day_offset"], hours=s["hour"])
        end = start + timedelta(minutes=s["duration"])
        sessions.append(SessionSchedule(
            name=s["name"],
            session_type=s["session_type"],
            start_time=start,
            end_time=end,
            duration_minutes=s["duration"],
        ))

    return RaceWeekendResponse(
        circuit_id=circuit.id,
        circuit_name=circuit.name,
        timezone=circuit.timezone,
        sessions=sessions,
    )


@router.get("/templates/list")
def list_templates():
    """List available race weekend templates."""
    return {
        name: {
            "sessions": len(tmpl),
            "session_names": [s["name"] for s in tmpl],
        }
        for name, tmpl in WEEKEND_TEMPLATES.items()
    }
