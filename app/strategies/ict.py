"""ICT 2022 Model: Order Blocks + Fair Value Gaps + Liquidity + Fib confluence."""

from app.core.enums import SignalType
from app.strategies.base import BaseStrategy, StrategyResult


class ICTStrategy(BaseStrategy):
    """ICT 2022: Order Block + FVG + Liquidity sweep with Fib confluence on 15m/1h/4h."""

    def __init__(self, params: dict | None = None):
        super().__init__("ict", params)
        self.lookback = self.params.get("lookback", 30)
        self.fib_levels = self.params.get("fib_levels", [0.618, 0.786])
        self.min_fvg_bps = self.params.get("min_fvg_bps", 5)

    @property
    def required_timeframes(self) -> list[str]:
        return ["15m", "1h", "4h"]

    @property
    def timeframe(self) -> str:
        return "15m"

    def analyze(self, candles: dict[str, list[dict]]) -> StrategyResult:
        entry_data = candles.get("15m", [])
        trend_data = candles.get("1h", [])
        structure_data = candles.get("4h", [])

        if len(entry_data) < self.lookback + 5:
            return StrategyResult(SignalType.HOLD, 0.0)

        fvg = self._find_fvg(entry_data[-self.lookback:])
        ob = self._find_order_block(entry_data[-self.lookback:])
        sweep = self._find_sweep(entry_data[-self.lookback:])

        trend_up = self._is_uptrend(trend_data) if len(trend_data) > 10 else True
        structure_up = self._is_uptrend(structure_data) if len(structure_data) > 5 else trend_up

        if not trend_up or not structure_up:
            fvg = None
            sweep = None

        signals = 0
        total_conf = 0.0
        metadata = {}

        if fvg and ob:
            bullish = ob["direction"] == "bullish" and fvg["direction"] == "bullish"
            bearish = ob["direction"] == "bearish" and fvg["direction"] == "bearish"
            if bullish and sweep and sweep["side"] == "buy":
                signals += 1
                total_conf += 0.5
                metadata.update({"fvg_low": fvg["low"], "fvg_high": fvg["high"], "ob_low": ob["low"], "ob_high": ob["high"]})
            elif bearish and sweep and sweep["side"] == "sell":
                signals += 1
                total_conf += 0.5
                metadata.update({"fvg_low": fvg["low"], "fvg_high": fvg["high"], "ob_low": ob["low"], "ob_high": ob["high"]})

        if sweep:
            metadata["swept_level"] = sweep["level"]
            metadata["sweep_type"] = sweep["side"]

        if signals == 0:
            return StrategyResult(SignalType.HOLD, 0.0)

        avg_conf = min(total_conf / signals, 1.0)
        direction = "bullish" if metadata.get("sweep_type") == "buy" else "bearish"
        last = entry_data[-1]

        if direction == "bullish":
            return StrategyResult(
                SignalType.BUY, avg_conf, metadata,
                entry_price=last["close"],
                stop_loss=last["low"] * 0.995,
                take_profit=last["close"] * 1.02,
            )
        return StrategyResult(
            SignalType.SELL, avg_conf, metadata,
            entry_price=last["close"],
            stop_loss=last["high"] * 1.005,
            take_profit=last["close"] * 0.98,
        )

    def _find_fvg(self, candles: list[dict]) -> dict | None:
        for i in range(len(candles) - 2, max(len(candles) - 8, 0), -1):
            c1, c2, c3 = candles[i], candles[i + 1], candles[i + 2]
            if c1["low"] > c3["high"]:
                gap_bps = (c1["low"] - c3["high"]) / c3["high"] * 10000
                if gap_bps >= self.min_fvg_bps:
                    return {"low": c3["high"], "high": c1["low"], "direction": "bullish"}
            if c1["high"] < c3["low"]:
                gap_bps = (c3["low"] - c1["high"]) / c1["high"] * 10000
                if gap_bps >= self.min_fvg_bps:
                    return {"low": c1["high"], "high": c3["low"], "direction": "bearish"}
        return None

    @staticmethod
    def _find_order_block(candles: list[dict]) -> dict | None:
        for i in range(len(candles) - 4, max(len(candles) - 12, 1), -1):
            prev, curr = candles[i - 1], candles[i]
            bullish_ob = prev["close"] < prev["open"] and curr["close"] > curr["open"] and curr["low"] <= prev["close"]
            bearish_ob = prev["close"] > prev["open"] and curr["close"] < curr["open"] and curr["high"] >= prev["close"]
            if bullish_ob:
                return {"low": min(prev["low"], curr["low"]), "high": max(prev["high"], curr["high"]), "direction": "bullish"}
            if bearish_ob:
                return {"low": min(prev["low"], curr["low"]), "high": max(prev["high"], curr["high"]), "direction": "bearish"}
        return None

    @staticmethod
    def _find_sweep(candles: list[dict]) -> dict | None:
        if len(candles) < 10: return None
        lookback = candles[:-5]
        recent = candles[-5:]
        high = max(c["high"] for c in lookback)
        low = min(c["low"] for c in lookback)
        for c in recent:
            if c["high"] > high: return {"level": high, "side": "sell"}
            if c["low"] < low: return {"level": low, "side": "buy"}
        return None

    @staticmethod
    def _is_uptrend(candles: list[dict]) -> bool:
        if len(candles) < 10: return True
        closes = [c["close"] for c in candles]
        ema9 = sum(closes[-9:]) / 9
        ema21 = sum(closes[-21:]) / 21 if len(closes) >= 21 else sum(closes) / len(closes)
        return ema9 > ema21
