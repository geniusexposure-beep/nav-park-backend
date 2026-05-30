from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime


# ─── Auth ─────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    name: str


# ─── Vehicle ──────────────────────────────────────────────────────────────────

class VehicleCreate(BaseModel):
    year: int
    make: str
    model: str
    color: str
    plate: str
    photo_url: Optional[str] = None

class VehicleOut(VehicleCreate):
    id: str
    user_id: str

    class Config:
        from_attributes = True


# ─── Driver State ─────────────────────────────────────────────────────────────

class LocationUpdate(BaseModel):
    latitude: float
    longitude: float

class StartNavigation(BaseModel):
    latitude: float
    longitude: float
    dest_lat: float
    dest_lng: float
    dest_name: str

class DriverStateOut(BaseModel):
    user_id: str
    status: str
    latitude: Optional[float]
    longitude: Optional[float]
    dest_lat: Optional[float]
    dest_lng: Optional[float]
    dest_name: Optional[str]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# ─── Parking ──────────────────────────────────────────────────────────────────

class VacatingRequest(BaseModel):
    latitude: float
    longitude: float
    address: Optional[str] = None

class MatchOut(BaseModel):
    match_id: str
    status: str
    space_lat: float
    space_lng: float
    space_address: Optional[str]
    pb_amount: int
    matched_at: datetime
    # vehicle info of the other party
    other_user_name: str
    other_vehicle_year: int
    other_vehicle_make: str
    other_vehicle_model: str
    other_vehicle_color: str
    other_vehicle_plate: str


# ─── Wallet ───────────────────────────────────────────────────────────────────

class WalletOut(BaseModel):
    user_id: str
    balance: int

class TransactionOut(BaseModel):
    id: str
    amount: int
    type: str
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class PurchaseRequest(BaseModel):
    amount: int   # Parking Bucks to purchase (maps to a $ price on the frontend)
