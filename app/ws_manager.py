"""
WebSocket connection manager + real-time event router.

Each connected driver holds one WebSocket. When a match is made,
the server pushes events to both sides directly through their connections.

Event types sent FROM client:
  update_location   { lat, lng }
  start_navigation  { lat, lng, dest_lat, dest_lng, dest_name }
  vacating          { lat, lng, address? }
  arrived           {}          # incoming driver confirms arrival

Event types pushed TO client:
  location_ack      confirmation of location update
  match_found       { match_id, other vehicle info, space coords, pb_amount }
  partner_location  { lat, lng }   # live position of matched partner
  partner_eta       { eta_seconds }
  match_complete    { pb_earned / pb_spent }
  error             { message }
"""

import json
import asyncio
import logging
from typing import Dict, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.models import (
    User, Vehicle, DriverState, DriverStatus,
    Wallet, Transaction, TxType, ParkingMatch, MatchStatus
)
from app.matching import (
    haversine, find_best_vacating_space, create_match,
    QUARTER_MILE_METERS, PB_PER_MATCH
)
from app.auth import SECRET_KEY, ALGORITHM
from jose import jwt, JWTError

logger = logging.getLogger(__name__)
router = APIRouter()

# user_id → WebSocket
active_connections: Dict[str, WebSocket] = {}
# user_id → match_id (so we know who's matched with whom)
active_matches: Dict[str, str] = {}


async def send(ws: WebSocket, event: str, data: dict):
    try:
        await ws.send_text(json.dumps({"event": event, **data}))
    except Exception:
        pass


async def push_to_user(user_id: str, event: str, data: dict):
    ws = active_connections.get(user_id)
    if ws:
        await send(ws, event, data)


@router.websocket("/connect")
async def ws_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
):
    # Authenticate via JWT passed as query param
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=4001)
            return
    except JWTError:
        await websocket.close(code=4001)
        return

    await websocket.accept()
    active_connections[user_id] = websocket
    logger.info(f"Driver connected: {user_id}")

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            event = msg.get("event")

            async with AsyncSessionLocal() as db:
                if event == "update_location":
                    await handle_location_update(db, user_id, msg, websocket)

                elif event == "start_navigation":
                    await handle_start_navigation(db, user_id, msg, websocket)

                elif event == "vacating":
                    await handle_vacating(db, user_id, msg, websocket)

                elif event == "arrived":
                    await handle_arrived(db, user_id, websocket)

                else:
                    await send(websocket, "error", {"message": f"Unknown event: {event}"})

    except WebSocketDisconnect:
        active_connections.pop(user_id, None)
        active_matches.pop(user_id, None)
        logger.info(f"Driver disconnected: {user_id}")
        async with AsyncSessionLocal() as db:
            await set_driver_idle(db, user_id)
