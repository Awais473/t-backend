from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.signal import Signal
from app.schemas.signal import SignalList, SignalResponse

router = APIRouter(prefix="/api/signals", tags=["signals"])


@router.get("/")
def get_signals(
    strategy_name: str | None = Query(None),
    symbol: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    q = db.query(Signal)
    if strategy_name:
        q = q.filter(Signal.strategy_name == strategy_name)
    if symbol:
        q = q.filter(Signal.symbol == symbol)
    rows = q.order_by(Signal.timestamp.desc()).limit(limit).all()
    signals = [SignalResponse.model_validate(s) for s in rows]
    return SignalList(signals=signals, total=len(signals))
