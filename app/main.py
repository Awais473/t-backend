from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import backtest, candles, performance, signals, strategies, strategy_metrics, trades, ws
from app.config import settings
from app.database import Base, engine
from app.services.binance_stream import stream_manager
from app.services.cache import init_cache


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_cache()
    Base.metadata.create_all(bind=engine)
    await stream_manager.start()
    yield
    await stream_manager.stop()


app = FastAPI(title="Trading Bot API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(candles.router)
app.include_router(strategies.router)
app.include_router(trades.router)
app.include_router(signals.router)
app.include_router(strategy_metrics.router)
app.include_router(performance.router)
app.include_router(backtest.router)
app.include_router(ws.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
