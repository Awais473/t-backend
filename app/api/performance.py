from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.strategy_metrics import StrategyMetrics
from app.schemas.strategy_metrics import StrategyMetricsList, StrategyMetricsResponse

router = APIRouter(prefix="/api/performance", tags=["performance"])


@router.get("/ranking")
def get_ranking(days: int | None = Query(None), db: Session = Depends(get_db)):
    q = db.query(StrategyMetrics)
    if days:
        from datetime import datetime, timezone
        from sqlalchemy import func
        cutoff = datetime.now(timezone.utc)
        q = q.filter(StrategyMetrics.last_updated >= cutoff)
    rows = q.order_by(StrategyMetrics.net_profit.desc()).all()
    return [
        {
            "rank": i + 1,
            "name": m.strategy_name,
            "symbol": m.symbol,
            "timeframe": m.timeframe,
            "total_trades": m.total_trades,
            "win_rate": round(m.win_rate, 2),
            "profit_factor": round(m.profit_factor, 2),
            "total_pnl": round(m.net_profit, 2),
            "max_drawdown": round(m.max_drawdown, 2),
            "sharpe_ratio": round(m.sharpe_ratio, 2),
            "avg_rr": round(m.average_rr, 2),
            "consecutive_wins": m.consecutive_wins,
            "consecutive_losses": m.consecutive_losses,
            "score": round(
                m.win_rate * 0.3
                + min(m.profit_factor, 10) * 10 * 0.3
                + min(m.sharpe_ratio, 3) * 33.3 * 0.4,
                2,
            ),
        }
        for i, m in enumerate(rows)
    ]


@router.get("/metrics")
def get_metrics(days: int | None = Query(None), db: Session = Depends(get_db)):
    from app.models.trade import Trade
    from datetime import datetime, timezone

    q = db.query(Trade).filter(Trade.status == "CLOSED")
    if days:
        cutoff = datetime.now(timezone.utc)
        q = q.filter(Trade.exit_time >= cutoff)

    closed = q.all()
    total = len(closed)
    wins = [t for t in closed if t.pnl and t.pnl > 0]
    losses = [t for t in closed if t.pnl and t.pnl <= 0]

    return {
        "total_trades": total,
        "closed_trades": total,
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "total_pnl": round(sum(t.pnl or 0 for t in closed), 2),
        "win_rate": round(len(wins) / total * 100, 2) if total > 0 else 0,
        "profit_factor": round(
            sum(t.pnl for t in wins) / abs(sum(t.pnl for t in losses)) if losses else float("inf"), 2
        ),
        "avg_rr": round(
            sum(t.rr_ratio or 0 for t in closed if t.rr_ratio)
            / max(len([t for t in closed if t.rr_ratio]), 1), 2
        ),
    }
