from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.strategy_config import StrategyConfig
from app.schemas.strategy import StrategyConfigCreate, StrategyConfigResponse
from app.services.active_strategies import activate, deactivate, is_active, list_active
from app.services.strategy_engine import get_strategy, get_candles_for_strategy, list_strategies as get_available_strategies


class ActivateRequest(BaseModel):
    strategy_name: str
    symbol: str
    timeframe: str = "15m"


class AnalysisResponse(BaseModel):
    strategy_name: str
    symbol: str
    timeframe: str
    signal: str
    confidence: float
    entry_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    metadata: dict


router = APIRouter(prefix="/api/strategies", tags=["strategies"])


@router.get("/")
def list_strategies():
    return get_available_strategies()


@router.get("/configs")
def get_configs(db: Session = Depends(get_db)):
    configs = db.query(StrategyConfig).all()
    return [StrategyConfigResponse.model_validate(c) for c in configs]


@router.post("/configs")
def create_config(payload: StrategyConfigCreate, db: Session = Depends(get_db)):
    existing = db.query(StrategyConfig).filter(StrategyConfig.name == payload.name).first()
    if existing:
        raise HTTPException(400, "Strategy config already exists")
    cfg = StrategyConfig(**payload.model_dump())
    db.add(cfg)
    db.commit()
    db.refresh(cfg)
    return StrategyConfigResponse.model_validate(cfg)


@router.patch("/configs/{name}")
def toggle_strategy(name: str, enabled: bool, db: Session = Depends(get_db)):
    cfg = db.query(StrategyConfig).filter(StrategyConfig.name == name).first()
    if not cfg:
        raise HTTPException(404, "Strategy not found")
    cfg.enabled = enabled
    db.commit()
    return StrategyConfigResponse.model_validate(cfg)


@router.post("/activate")
def activate_strategy(payload: ActivateRequest):
    s = get_strategy(payload.strategy_name)
    if not s:
        raise HTTPException(404, "Strategy not found")
    return activate(payload.strategy_name, payload.symbol, payload.timeframe)


@router.post("/deactivate")
def deactivate_strategy(payload: ActivateRequest):
    if not deactivate(payload.strategy_name, payload.symbol):
        raise HTTPException(404, "Active strategy not found")
    return {"ok": True}


@router.get("/active")
def list_active_strategies():
    return list_active()


@router.post("/analyze")
def analyze_strategy(payload: ActivateRequest):
    s = get_strategy(payload.strategy_name, {"timeframe": payload.timeframe})
    if not s:
        raise HTTPException(404, "Strategy not found")
    all_candles = get_candles_for_strategy(s, payload.symbol)
    primary = all_candles.get(payload.timeframe, [])
    if not primary:
        raise HTTPException(400, "No candle data for this symbol/timeframe")
    result = s.analyze(all_candles)
    return AnalysisResponse(
        strategy_name=payload.strategy_name,
        symbol=payload.symbol,
        timeframe=payload.timeframe,
        signal=result.signal.value,
        confidence=result.confidence,
        entry_price=result.entry_price,
        stop_loss=result.stop_loss,
        take_profit=result.take_profit,
        metadata=result.metadata or {},
    )
