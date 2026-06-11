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
    # SMC-specific params
    swing_length: int = Query(50, ge=5, le=200),
    show_internals: bool = Query(True),
    show_swing: bool = Query(True),
    show_internal_ob: bool = Query(True),
    show_swing_ob: bool = Query(False),
    internal_ob_count: int = Query(5, ge=1, le=20),
    swing_ob_count: int = Query(5, ge=1, le=20),
    ob_filter: str = Query("atr"),
    ob_mitigation: str = Query("high_low"),
    show_fvg: bool = Query(False),
    fvg_threshold: bool = Query(True),
    show_eqh_eql: bool = Query(True),
    eqh_eql_length: int = Query(3, ge=1, le=20),
    eqh_eql_threshold: float = Query(0.1, ge=0, le=0.5),
    show_swing_points: bool = Query(False),
    show_zones: bool = Query(False),
    show_strong_weak: bool = Query(True),
    show_mtf: bool = Query(False),
    show_trend_candles: bool = Query(False),
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
        swing_length=swing_length,
        show_internals=show_internals,
        show_swing=show_swing,
        show_internal_ob=show_internal_ob,
        show_swing_ob=show_swing_ob,
        internal_ob_count=internal_ob_count,
        swing_ob_count=swing_ob_count,
        ob_filter=ob_filter,
        ob_mitigation=ob_mitigation,
        show_fvg=show_fvg,
        fvg_threshold=fvg_threshold,
        show_eqh_eql=show_eqh_eql,
        eqh_eql_length=eqh_eql_length,
        eqh_eql_threshold=eqh_eql_threshold,
        show_swing_points=show_swing_points,
        show_zones=show_zones,
        show_strong_weak=show_strong_weak,
        show_mtf=show_mtf,
        show_trend_candles=show_trend_candles,
    )

    return {
        "indicator": result.indicator,
        "params": result.params,
        "data": result.data,
    }


@router.get("/list")
def list_all_indicators():
    return list_indicators()
