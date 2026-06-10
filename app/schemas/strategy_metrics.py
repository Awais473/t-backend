from datetime import datetime

from pydantic import BaseModel


class StrategyMetricsBase(BaseModel):
    strategy_name: str
    symbol: str
    timeframe: str
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    average_rr: float = 0.0
    max_drawdown: float = 0.0
    net_profit: float = 0.0
    sharpe_ratio: float = 0.0
    consecutive_wins: int = 0
    consecutive_losses: int = 0
    last_trade_result: str | None = None


class StrategyMetricsResponse(StrategyMetricsBase):
    id: int
    last_updated: datetime

    model_config = {"from_attributes": True}


class StrategyMetricsList(BaseModel):
    metrics: list[StrategyMetricsResponse]
    total: int
