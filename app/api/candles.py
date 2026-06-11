from fastapi import APIRouter, HTTPException, Query

from app.services.data_collector import BinanceCollector

router = APIRouter(prefix="/api/candles", tags=["candles"])

MAX_LIMIT = 5000


@router.get("/")
def get_candles(
    symbol: str = Query(...),
    timeframe: str = Query("1h"),
    limit: int = Query(200, ge=1, le=MAX_LIMIT),
    start_time: int | None = Query(None, description="Start time in seconds since epoch"),
    end_time: int | None = Query(None, description="End time in seconds since epoch"),
):
    try:
        collector = BinanceCollector()
        if start_time is not None or end_time is not None:
            fetched = collector.fetch_klines_range(symbol, timeframe, start_time, end_time, limit)
        else:
            fetched = collector.fetch_klines(symbol, timeframe, limit)
        return {"candles": fetched, "total": len(fetched)}
    except Exception as e:
        raise HTTPException(404, f"No candle data available: {e}")


@router.get("/symbols")
def get_symbols():
    return ["BTCUSDT", "ETHUSDT"]
