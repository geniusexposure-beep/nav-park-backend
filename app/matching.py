"""
Core matching logic.

Uses the Haversine formula for ¼-mile radius checks — no PostGIS extension
required, works on any standard PostgreSQL instance (Railway included).

PostGIS would be faster at scale (10k+ drivers), but Haversine in Python
is perfectly fine for an MVP.
"""

import math
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import DriverState, DriverStatus, User, Vehicle, ParkingMatch, MatchStatus

QUARTER_MILE_METERS = 402.336   # ¼ mile in meters
PB_PER_MATCH        = 15        # Parking Bucks charged/earned per handoff


def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Return distance in meters between two GPS coordinates."""
    R = 6_371_000  # Earth radius in metres
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    Δφ = math.radians(lat2 - lat1)
    Δλ = math.radians(lng2 - lng1)
    a = math.sin(Δφ / 2) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(Δλ / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


async def find_best_vacating_space(
    db: AsyncSession,
    incoming_user_id: str,
    dest_lat: float,
    dest_lng: float,
    incoming_lat: float,
    incoming_lng: float,
) -> Optional[DriverState]:
    """
    Find the closest vacating driver to the incoming driver,
    provided that vacating driver is within ¼ mile of the destination.

    Returns the DriverState of the best match, or None.
    """
    result = await db.execute(
        select(DriverState)
        .options(selectinload(DriverState.user).selectinload(User.vehicle))
        .where(
            DriverState.status == DriverStatus.vacating,
            DriverState.user_id != incoming_user_id,
            DriverState.latitude.isnot(None),
        )
    )
    candidates = result.scalars().all()

    best: Optional[DriverState] = None
    best_dist = float("inf")

    for state in candidates:
        # 1. Must be within ¼ mile of the destination
        dist_to_dest = haversine(state.latitude, state.longitude, dest_lat, dest_lng)
        if dist_to_dest > QUARTER_MILE_METERS:
            continue

        # 2. Pick the one closest to the incoming driver
        dist_to_incoming = haversine(state.latitude, state.longitude, incoming_lat, incoming_lng)
        if dist_to_incoming < best_dist:
            best_dist = dist_to_incoming
            best = state

    return best


async def create_match(
    db: AsyncSession,
    vacating_state: DriverState,
    incoming_user_id: str,
) -> ParkingMatch:
    """Create a ParkingMatch row and mark both drivers as matched."""
    match = ParkingMatch(
        vacating_user_id = vacating_state.user_id,
        incoming_user_id = incoming_user_id,
        status           = MatchStatus.active,
        space_lat        = vacating_state.latitude,
        space_lng        = vacating_state.longitude,
        pb_amount        = PB_PER_MATCH,
    )
    db.add(match)

    # Update both driver states
    vacating_state.status = DriverStatus.matched

    incoming_result = await db.execute(
        select(DriverState).where(DriverState.user_id == incoming_user_id)
    )
    incoming_state = incoming_result.scalar_one_or_none()
    if incoming_state:
        incoming_state.status = DriverStatus.matched

    await db.commit()
    await db.refresh(match)
    return match
