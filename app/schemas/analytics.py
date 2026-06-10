from pydantic import BaseModel


class PerformanceMetrics(BaseModel):
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    total_pnl: float
    max_drawdown: float
    sharpe_ratio: float
    avg_win: float
    avg_loss: float
    avg_holding_period: float | None = None


class StrategyRanking(BaseModel):
    rank: int
    name: str
    win_rate: float
    profit_factor: float
    total_pnl: float
    max_drawdown: float
    sharpe_ratio: float
    score: float
