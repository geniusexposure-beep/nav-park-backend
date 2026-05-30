"""
Parking routes: match history, active match status.

Note: vacating, navigation, and arrived events flow through WebSocket
(ws_manager.py) for real-time push. These REST endpoints are for
polling/history use cases and the mobile app's initial state load.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import User, ParkingMatch, MatchStatus, Vehicle
from app.auth import get_current_user

router = APIRouter()


@router.get("/matches", response_model=List[dict])
async def get_match_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 20,
):
    """Return the last N matches (as vacating or incoming driver)."""
    result = await db.execute(
        select(ParkingMatch)
        .where(
            or_(
                ParkingMatch.vacating_user_id == current_user.id,
                ParkingMatch.incoming_user_id == current_user.id,
            )
        )
        .order_by(ParkingMatch.matched_at.desc())
        .limit(limit)
    )
    matches = result.scalars().all()

    out = []
    for m in matches:
        role = "vacating" if m.vacating_user_id == current_user.id else "incoming"
        out.append({
            "match_id":      m.id,
            "role":          role,
            "status":        m.status,
            "space_lat":     m.space_lat,
            "space_lng":     m.space_lng,
            "space_address": m.space_address,
            "pb_amount":     m.pb_amount,
            "matched_at":    m.matched_at.isoformat() if m.matched_at else None,
            "completed_at":  m.completed_at.isoformat() if m.completed_at else None,
        })
    return out


@router.get("/matches/active", response_model=Optional[dict])
async def get_active_match(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the current active match if one exists, else null."""
    result = await db.execute(
        select(ParkingMatch)
        .options(
            selectinload(ParkingMatch.vacating_user).selectinload(User.vehicle),
            selectinload(ParkingMatch.incoming_user).selectinload(User.vehicle),
        )
        .where(
            ParkingMatch.status == MatchStatus.active,
            or_(
                ParkingMatch.vacating_user_id == current_user.id,
                ParkingMatch.incoming_user_id == current_user.id,
            )
        )
    )
    match = result.scalar_one_or_none()
    if not match:
        return None

    role = "vacating" if match.vacating_user_id == current_user.id else "incoming"
    other_user = match.incoming_user if role == "vacating" else match.vacating_user
    other_vehicle: Optional[Vehicle] = other_user.vehicle if other_user else None

    return {
        "match_id":          match.id,
        "role":              role,
        "status":            match.status,
        "space_lat":         match.space_lat,
        "space_lng":         match.space_lng,
        "space_address":     match.space_address,
        "pb_amount":         match.pb_amount,
        "matched_at":        match.matched_at.isoformat() if match.matched_at else None,
        "other_name":        other_user.name if other_user else "",
        "other_year":        other_vehicle.year  if other_vehicle else 0,
        "other_make":        other_vehicle.make  if other_vehicle else "",
        "other_model":       other_vehicle.model if other_vehicle else "",
        "other_color":       other_vehicle.color if other_vehicle else "",
        "other_plate":       other_vehicle.plate if other_vehicle else "",
    }
