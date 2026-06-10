from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.strategy_metrics import StrategyMetrics
from app.schemas.strategy_metrics import StrategyMetricsList, StrategyMetricsResponse

router = APIRouter(prefix="/api/strategy-metrics", tags=["strategy-metrics"])


@router.get("/")
def get_strategy_metrics(
    strategy_name: str | None = Query(None),
    symbol: str | None = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(StrategyMetrics)
    if strategy_name:
        q = q.filter(StrategyMetrics.strategy_name == strategy_name)
    if symbol:
        q = q.filter(StrategyMetrics.symbol == symbol)
    rows = q.order_by(StrategyMetrics.last_updated.desc()).all()
    metrics = [StrategyMetricsResponse.model_validate(m) for m in rows]
    return StrategyMetricsList(metrics=metrics, total=len(metrics))
