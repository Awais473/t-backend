from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.backtesting_engine import BacktestingEngine

router = APIRouter(prefix="/api/backtest", tags=["backtest"])


class BacktestRequest(BaseModel):
    strategy_name: str
    symbol: str
    timeframe: str = "1h"
    limit: int = 500
    initial_capital: float = 10000.0


@router.post("/")
def run_backtest(req: BacktestRequest):
    engine = BacktestingEngine(req.initial_capital)
    result = engine.run(req.strategy_name, req.symbol, req.timeframe, req.limit)
    return {
        "total_trades": len(result.trades),
        "winning_trades": result.winning_trades,
        "losing_trades": result.losing_trades,
        "total_pnl": round(result.total_pnl, 2),
        "win_rate": round(result.winning_trades / len(result.trades) * 100, 2) if result.trades else 0,
        "profit_factor": round(result.profit_factor, 2),
        "max_drawdown": round(result.max_drawdown, 2),
        "sharpe_ratio": round(result.sharpe_ratio, 2),
        "trades": [
            {
                "entry_time": t.entry_time.isoformat(),
                "exit_time": t.exit_time.isoformat() if t.exit_time else None,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "side": t.side,
                "pnl": round(t.pnl, 2),
                "pnl_percent": round(t.pnl_percent, 2) if t.pnl_percent else 0,
            }
            for t in result.trades
        ],
    }
