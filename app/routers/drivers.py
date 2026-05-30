"""
Driver routes: vehicle CRUD + driver state.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import User, Vehicle, DriverState, DriverStatus
from app.schemas import VehicleCreate, VehicleOut, DriverStateOut
from app.auth import get_current_user

router = APIRouter()


# ─── Vehicle ──────────────────────────────────────────────────────────────────

@router.post("/vehicle", response_model=VehicleOut, status_code=201)
async def add_vehicle(
    body: VehicleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Only one vehicle per user
    result = await db.execute(select(Vehicle).where(Vehicle.user_id == current_user.id))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Vehicle already registered. Use PUT to update.")

    vehicle = Vehicle(user_id=current_user.id, **body.model_dump())
    db.add(vehicle)
    await db.commit()
    await db.refresh(vehicle)
    return vehicle


@router.get("/vehicle", response_model=VehicleOut)
async def get_vehicle(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Vehicle).where(Vehicle.user_id == current_user.id))
    vehicle = result.scalar_one_or_none()
    if not vehicle:
        raise HTTPException(status_code=404, detail="No vehicle registered")
    return vehicle


@router.put("/vehicle", response_model=VehicleOut)
async def update_vehicle(
    body: VehicleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Vehicle).where(Vehicle.user_id == current_user.id))
    vehicle = result.scalar_one_or_none()
    if not vehicle:
        raise HTTPException(status_code=404, detail="No vehicle registered. Use POST to create.")

    for field, value in body.model_dump().items():
        setattr(vehicle, field, value)
    await db.commit()
    await db.refresh(vehicle)
    return vehicle


@router.delete("/vehicle", status_code=204)
async def delete_vehicle(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Vehicle).where(Vehicle.user_id == current_user.id))
    vehicle = result.scalar_one_or_none()
    if vehicle:
        await db.delete(vehicle)
        await db.commit()


# ─── Driver State ─────────────────────────────────────────────────────────────

@router.get("/state", response_model=DriverStateOut)
async def get_driver_state(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DriverState).where(DriverState.user_id == current_user.id)
    )
    state = result.scalar_one_or_none()
    if not state:
        # Return default idle state without persisting
        return DriverStateOut(
            user_id   = current_user.id,
            status    = DriverStatus.idle,
            latitude  = None,
            longitude = None,
            dest_lat  = None,
            dest_lng  = None,
            dest_name = None,
            updated_at = None,
        )
    return state
