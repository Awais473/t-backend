from datetime import datetime

from pydantic import BaseModel


class SignalBase(BaseModel):
    strategy_name: str
    symbol: str
    timeframe: str
    signal: str
    price: float
    entry_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    confidence: float | None = None
    extra_data: str | None = None
    timestamp: datetime


class SignalCreate(SignalBase):
    pass


class SignalResponse(SignalBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class SignalList(BaseModel):
    signals: list[SignalResponse]
    total: int
