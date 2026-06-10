from app.core.enums import SignalType
from app.strategies.base import BaseStrategy, StrategyResult


class FibonacciRetracementStrategy(BaseStrategy):
    """Fibonacci Retracement: Bounce off key Fib levels with trend confirmation."""

    def __init__(self, params: dict | None = None):
        super().__init__("fib_retracement", params)
        self.lookback = self.params.get("lookback", 50)
        self.fib_levels = self.params.get("fib_levels", [0.382, 0.5, 0.618])

    @property
    def required_timeframes(self) -> list[str]:
        return [self.timeframe, "1h"]

    def analyze(self, candles: dict[str, list[dict]]) -> StrategyResult:
        tf = self.timeframe
        data = candles.get(tf, [])
        trend_data = candles.get("1h", data)

        if len(data) < self.lookback or len(trend_data) < self.lookback:
            return StrategyResult(SignalType.HOLD, 0.0)

        swing_high = max(c["high"] for c in data[-self.lookback:])
        swing_low = min(c["low"] for c in data[-self.lookback:])
        diff = swing_high - swing_low

        trend_high = max(c["high"] for c in trend_data[-self.lookback:])
        trend_low = min(c["low"] for c in trend_data[-self.lookback:])
        uptrend = trend_data[-1]["close"] > (trend_high + trend_low) / 2

        last = data[-1]
        for level in self.fib_levels:
            fib_price = swing_high - diff * level
            if uptrend and abs(last["low"] - fib_price) / fib_price < 0.003:
                return StrategyResult(
                    SignalType.BUY, 0.65,
                    {"level": level, "fib_price": fib_price},
                    entry_price=last["close"],
                    stop_loss=fib_price * 0.99,
                    take_profit=swing_high,
                )
            if not uptrend and abs(last["high"] - fib_price) / fib_price < 0.003:
                return StrategyResult(
                    SignalType.SELL, 0.65,
                    {"level": level, "fib_price": fib_price},
                    entry_price=last["close"],
                    stop_loss=fib_price * 1.01,
                    take_profit=swing_low,
                )

        return StrategyResult(SignalType.HOLD, 0.0)
