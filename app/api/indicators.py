from fastapi import APIRouter, HTTPException, Query

from app.indicators import get_indicator, list_indicators
from app.services.data_collector import BinanceCollector

router = APIRouter(prefix="/api/indicators", tags=["indicators"])


@router.get("/")
def get_indicator_data(
    symbol: str = Query(...),
    timeframe: str = Query("1h"),
    indicator: str = Query(...),
    period: int = Query(14, ge=1, le=500),
    fast_period: int = Query(12, ge=1, le=100),
    slow_period: int = Query(26, ge=1, le=200),
    signal_period: int = Query(9, ge=1, le=50),
    source: str = Query("close"),
    lookback: int = Query(50, ge=5, le=500),
):
    cls = get_indicator(indicator)
    if not cls:
        raise HTTPException(404, f"Indicator '{indicator}' not found")

    collector = BinanceCollector()
    candles = collector.fetch_klines(symbol, timeframe, 500)

    candle_dicts = [
        {
            "open": c["open"],
            "high": c["high"],
            "low": c["low"],
            "close": c["close"],
            "volume": c["volume"],
            "timestamp": c["timestamp"],
        }
        for c in candles
    ]

    inst = cls()
    result = inst.calculate(
        candle_dicts,
        period=period,
        fast_period=fast_period,
        slow_period=slow_period,
        signal_period=signal_period,
        source=source,
        lookback=lookback,
    )

    return {
        "indicator": result.indicator,
        "params": result.params,
        "data": result.data,
    }


@router.get("/list")
def list_all_indicators():
    return list_indicators()
