"""
Core matching logic.
"""

import math
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import DriverState, DriverStatus, User, Vehicle, ParkingMatch, MatchStatus