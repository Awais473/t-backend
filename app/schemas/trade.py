from datetime import datetime

from pydantic import BaseModel


class TradeBase(BaseModel):
    strategy_name: str
    symbol: str
    side: str
    timeframe: str = "1h"
    entry_price: float
    exit_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    quantity: float
    entry_time: datetime
    exit_time: datetime | None = None
    pnl: float | None = None
    pnl_percent: float | None = None
    rr_ratio: float | None = None
    duration_minutes: int | None = None
    result: str | None = None
    status: str = "OPEN"


class TradeCreate(TradeBase):
    pass


class TradeResponse(TradeBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class TradeList(BaseModel):
    trades: list[TradeResponse]
    total: int
