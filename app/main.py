from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.database import engine, Base
from app.routers import auth, drivers, parking, wallet
from app.ws_manager import router as ws_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Nav & Park backend started")
    yield
    logger.info("Nav & Park backend shutting down")


app = FastAPI(
    title="Nav & Park API",
    description="Real-time parking space matching platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,    prefix="/auth",    tags=["Auth"])
app.include_router(drivers.router, prefix="/drivers", tags=["Drivers"])
app.include_router(parking.router, prefix="/parking", tags=["Parking"])
app.include_router(wallet.router,  prefix="/wallet",  tags=["Wallet"])
app.include_router(ws_router,      prefix="/ws",      tags=["WebSocket"])


@app.get("/")
async def root():
    return {"status": "Nav & Park API running", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "ok"}
