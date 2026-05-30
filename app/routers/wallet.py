"""
Wallet routes: balance, transaction history, purchase Parking Bucks.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import User, Wallet, Transaction, TxType
from app.schemas import WalletOut, TransactionOut, PurchaseRequest
from app.auth import get_current_user

router = APIRouter()

# Price tiers: PB amount → USD cents
PB_PRICE_MAP = {
    50:  99,
    150: 249,
    500: 699,
}
