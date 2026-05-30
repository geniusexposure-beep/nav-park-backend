from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime,
    ForeignKey, Enum, Text, func
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


# ─── Enums ────────────────────────────────────────────────────────────────────

class DriverStatus(str, enum.Enum):
    idle       = "idle"
    navigating = "navigating"   # driving toward a destination
    vacating   = "vacating"     # sitting in a space, about to leave
    matched    = "matched"      # assigned to a handoff

class MatchStatus(str, enum.Enum):
    pending   = "pending"
    active    = "active"        # both parties notified
    completed = "completed"     # space handed off
    cancelled = "cancelled"

class TxType(str, enum.Enum):
    earn     = "earn"      # held a space
    spend    = "spend"     # used a space
    purchase = "purchase"  # bought Parking Bucks
    bonus    = "bonus"     # welcome / promotional


# ─── Users ────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id            = Column(String, primary_key=True, default=gen_uuid)
    name          = Column(String(100), nullable=False)
    email         = Column(String(255), unique=True, nullable=False, index=True)
    phone         = Column(String(20), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    is_active     = Column(Boolean, default=True)

    vehicle       = relationship("Vehicle", back_populates="user", uselist=False)
    wallet        = relationship("Wallet",  back_populates="user", uselist=False)
    transactions  = relationship("Transaction", back_populates="user")
    driver_state  = relationship("DriverState", back_populates="user", uselist=False)


# ─── Vehicles ─────────────────────────────────────────────────────────────────

class Vehicle(Base):
    __tablename__ = "vehicles"

    id        = Column(String, primary_key=True, default=gen_uuid)
    user_id   = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    year      = Column(Integer, nullable=False)
    make      = Column(String(50), nullable=False)
    model     = Column(String(100), nullable=False)
    color     = Column(String(50), nullable=False)
    plate     = Column(String(20), nullable=False)
    photo_url = Column(Text, nullable=True)

    user = relationship("User", back_populates="vehicle")


# ─── Driver State (live GPS + status) ─────────────────────────────────────────
# One row per user. Updated in real time as the driver moves.

class DriverState(Base):
    __tablename__ = "driver_states"

    user_id       = Column(String, ForeignKey("users.id"), primary_key=True)
    status        = Column(Enum(DriverStatus), default=DriverStatus.idle, nullable=False)

    # Current GPS position
    latitude      = Column(Float, nullable=True)
    longitude     = Column(Float, nullable=True)

    # Where they're navigating TO (set when status = navigating)
    dest_lat      = Column(Float, nullable=True)
    dest_lng      = Column(Float, nullable=True)
    dest_name     = Column(String(200), nullable=True)

    updated_at    = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="driver_state")


# ─── Parking Matches ──────────────────────────────────────────────────────────

class ParkingMatch(Base):
    __tablename__ = "parking_matches"

    id               = Column(String, primary_key=True, default=gen_uuid)
    vacating_user_id = Column(String, ForeignKey("users.id"), nullable=False)
    incoming_user_id = Column(String, ForeignKey("users.id"), nullable=False)
    status           = Column(Enum(MatchStatus), default=MatchStatus.pending)

    # Space location (vacating driver's position at time of match)
    space_lat        = Column(Float, nullable=False)
    space_lng        = Column(Float, nullable=False)
    space_address    = Column(String(200), nullable=True)

    # Parking Bucks transferred
    pb_amount        = Column(Integer, default=15)

    matched_at       = Column(DateTime(timezone=True), server_default=func.now())
    completed_at     = Column(DateTime(timezone=True), nullable=True)

    vacating_user    = relationship("User", foreign_keys=[vacating_user_id])
    incoming_user    = relationship("User", foreign_keys=[incoming_user_id])


# ─── Parking Bucks Wallet ─────────────────────────────────────────────────────

class Wallet(Base):
    __tablename__ = "wallets"

    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    balance = Column(Integer, default=50)   # 50 PB welcome bonus

    user = relationship("User", back_populates="wallet")


class Transaction(Base):
    __tablename__ = "transactions"

    id          = Column(String, primary_key=True, default=gen_uuid)
    user_id     = Column(String, ForeignKey("users.id"), nullable=False)
    amount      = Column(Integer, nullable=False)   # positive = credit, negative = debit
    type        = Column(Enum(TxType), nullable=False)
    description = Column(String(255), nullable=True)
    match_id    = Column(String, ForeignKey("parking_matches.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="transactions")
