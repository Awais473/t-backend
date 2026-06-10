from app.core.enums import SignalType
from app.strategies.base import BaseStrategy, StrategyResult


class LiquiditySweepStrategy(BaseStrategy):
    """Liquidity Sweep: Detect stop hunts above highs / below lows, then trade reversal."""

    def __init__(self, params: dict | None = None):
        super().__init__("liquidity_sweep", params)
        self.lookback = self.params.get("lookback", 20)
        self.reversal_candles = self.params.get("reversal_candles", 2)

    @property
    def required_timeframes(self) -> list[str]:
        return [self.timeframe, "1h"]

    def analyze(self, candles: dict[str, list[dict]]) -> StrategyResult:
        tf = self.timeframe
        data = candles.get(tf, [])
        trend_data = candles.get("1h", data)

        if len(data) < self.lookback + self.reversal_candles:
            return StrategyResult(SignalType.HOLD, 0.0)

        lookback_candles = data[:self.lookback]
        recent_candles = data[self.lookback:self.lookback + self.reversal_candles]

        high = max(c["high"] for c in lookback_candles)
        low = min(c["low"] for c in lookback_candles)

        trend_close = trend_data[-1]["close"] if trend_data else data[-1]["close"]
        trend_high = max(c["high"] for c in (trend_data[-self.lookback:] if len(trend_data) >= self.lookback else trend_data))
        trend_low = min(c["low"] for c in (trend_data[-self.lookback:] if len(trend_data) >= self.lookback else trend_data))
        uptrend = trend_close > (trend_high + trend_low) / 2 if trend_high != trend_low else True

        for c in recent_candles:
            if c["high"] > high and not uptrend:
                candle_body = abs(c["close"] - c["open"])
                sweep_size = abs(c["high"] - c["low"])
                confidence = min(sweep_size / candle_body * 0.5, 1.0) if candle_body > 0 else 0.3
                return StrategyResult(
                    SignalType.SELL, confidence,
                    {"swept_level": high, "sweep_type": "resistance"},
                    entry_price=c["close"],
                    stop_loss=c["high"] * 1.01,
                    take_profit=low,
                )
            if c["low"] < low and uptrend:
                candle_body = abs(c["close"] - c["open"])
                sweep_size = abs(c["high"] - c["low"])
                confidence = min(sweep_size / candle_body * 0.5, 1.0) if candle_body > 0 else 0.3
                return StrategyResult(
                    SignalType.BUY, confidence,
                    {"swept_level": low, "sweep_type": "support"},
                    entry_price=c["close"],
                    stop_loss=c["low"] * 0.99,
                    take_profit=high,
                )

        return StrategyResult(SignalType.HOLD, 0.0)
