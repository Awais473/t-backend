from fastapi import APIRouter, HTTPException, Query

from app.services.data_collector import BinanceCollector

router = APIRouter(prefix="/api/candles", tags=["candles"])


@router.get("/")
def get_candles(
    symbol: str = Query(...),
    timeframe: str = Query("1h"),
    limit: int = Query(200, ge=1, le=1000),
):
    try:
        collector = BinanceCollector()
        fetched = collector.fetch_klines(symbol, timeframe, limit)
        return {"candles": fetched, "total": len(fetched)}
    except Exception:
        raise HTTPException(404, "No candle data available")


@router.get("/symbols")
def get_symbols():
    return ["BTCUSDT", "ETHUSDT"]
