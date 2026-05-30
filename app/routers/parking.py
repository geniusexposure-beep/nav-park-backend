"""
Parking routes: match history, active match status.
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
