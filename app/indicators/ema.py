from app.indicators.base import BaseIndicator, IndicatorResult


class EMAIndicator(BaseIndicator):
    """Exponential Moving Average"""

    def __init__(self):
        super().__init__()
        self.name = "ema"

    @property
    def description(self) -> str:
        return "Exponential Moving Average"

    def calculate(self, candles: list[dict], **params) -> IndicatorResult:
        period = int(params.get("period", 20))
        source = params.get("source", "close")
        if len(candles) < period:
            return IndicatorResult("EMA", [], {"period": period, "source": source})

        prices = [c[source] for c in candles]
        multiplier = 2 / (period + 1)
        ema = [sum(prices[:period]) / period]
        for v in prices[period:]:
            ema.append((v - ema[-1]) * multiplier + ema[-1])

        data = []
        offset = len(candles) - len(ema)
        for i, v in enumerate(ema):
            data.append({
                "time": self._to_seconds(candles[offset + i]["timestamp"]),
                "value": round(v, 2),
            })
        return IndicatorResult("EMA", data, {"period": period, "source": source})
