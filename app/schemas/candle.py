from datetime import datetime

from pydantic import BaseModel


class CandleBase(BaseModel):
    symbol: str
    timeframe: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: datetime


class CandleCreate(CandleBase):
    pass


class CandleResponse(CandleBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class CandleList(BaseModel):
    candles: list[CandleResponse]
    total: int
