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

# Price tiers: PB amount → USD cents (e.g. 50 PB = $0.99)
PB_PRICE_MAP = {
    50:  99,    # $0.99
    150: 249,   # $2.49
    500: 699,   # $6.99
}


@router.get("/balance", response_model=WalletOut)
async def get_balance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    wallet = await db.get(Wallet, current_user.id)
    if not wallet:
        # Auto-create wallet (shouldn't happen after register, but just in case)
        wallet = Wallet(user_id=current_user.id, balance=0)
        db.add(wallet)
        await db.commit()
        await db.refresh(wallet)
    return wallet


@router.get("/transactions", response_model=List[TransactionOut])
async def get_transactions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
):
    result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == current_user.id)
        .order_by(Transaction.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.post("/purchase", response_model=WalletOut)
async def purchase_parking_bucks(
    body: PurchaseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Purchase Parking Bucks. In production this would integrate with
    Stripe/Apple Pay/Google Pay before crediting the wallet.
    For MVP we credit immediately (payment integration is a Phase 2 task).
    """
    if body.amount not in PB_PRICE_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid amount. Choose from: {list(PB_PRICE_MAP.keys())}"
        )

    wallet = await db.get(Wallet, current_user.id)
    if not wallet:
        wallet = Wallet(user_id=current_user.id, balance=0)
        db.add(wallet)
        await db.flush()

    wallet.balance += body.amount
    db.add(Transaction(
        user_id     = current_user.id,
        amount      = body.amount,
        type        = TxType.purchase,
        description = f"Purchased {body.amount} Parking Bucks",
    ))
    await db.commit()
    await db.refresh(wallet)
    return wallet
