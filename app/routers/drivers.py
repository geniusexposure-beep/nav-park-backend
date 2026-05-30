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
