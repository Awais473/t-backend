from datetime import datetime

from pydantic import BaseModel


class StrategyConfigBase(BaseModel):
    name: str
    description: str | None = None
    enabled: bool = True
    params: str | None = None


class StrategyConfigCreate(StrategyConfigBase):
    pass


class StrategyConfigResponse(StrategyConfigBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StrategyPerformance(BaseModel):
    name: str
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
