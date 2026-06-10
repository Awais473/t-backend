from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.trade import Trade
from app.schemas.trade import TradeList, TradeResponse

router = APIRouter(prefix="/api/trades", tags=["trades"])


@router.get("/")
def get_trades(
    strategy_name: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    q = db.query(Trade)
    if strategy_name:
        q = q.filter(Trade.strategy_name == strategy_name)
    rows = q.order_by(Trade.entry_time.desc()).limit(limit).all()
    trades = [TradeResponse.model_validate(t) for t in rows]
    return TradeList(trades=trades, total=len(trades))
