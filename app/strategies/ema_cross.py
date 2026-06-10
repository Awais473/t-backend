from app.core.enums import SignalType
from app.strategies.base import BaseStrategy, StrategyResult


class EMACrossStrategy(BaseStrategy):
    """EMA Crossover: Fast EMA crosses above/below Slow EMA."""

    def __init__(self, params: dict | None = None):
        super().__init__("ema_cross", params)
        self.fast_period = self.params.get("fast_period", 9)
        self.slow_period = self.params.get("slow_period", 21)

    def analyze(self, candles: dict[str, list[dict]]) -> StrategyResult:
        tf = self.timeframe
        data = candles.get(tf, [])
        if len(data) < self.slow_period + 2:
            return StrategyResult(SignalType.HOLD, 0.0)

        closes = [c["close"] for c in data]
        fast_ema = self._ema(closes, self.fast_period)
        slow_ema = self._ema(closes, self.slow_period)

        if len(fast_ema) < 2 or len(slow_ema) < 2:
            return StrategyResult(SignalType.HOLD, 0.0)

        bullish = fast_ema[-2] <= slow_ema[-2] and fast_ema[-1] > slow_ema[-1]
        bearish = fast_ema[-2] >= slow_ema[-2] and fast_ema[-1] < slow_ema[-1]

        last = data[-1]
        if bullish:
            return StrategyResult(
                SignalType.BUY, 0.7,
                {"fast_ema": fast_ema[-1], "slow_ema": slow_ema[-1]},
                entry_price=last["close"],
            )
        if bearish:
            return StrategyResult(
                SignalType.SELL, 0.7,
                {"fast_ema": fast_ema[-1], "slow_ema": slow_ema[-1]},
                entry_price=last["close"],
            )
        return StrategyResult(SignalType.HOLD, 0.0)

    @staticmethod
    def _ema(values: list[float], period: int) -> list[float]:
        if len(values) < period:
            return []
        multiplier = 2 / (period + 1)
        ema = [sum(values[:period]) / period]
        for v in values[period:]:
            ema.append((v - ema[-1]) * multiplier + ema[-1])
        return ema
