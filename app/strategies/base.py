from abc import ABC, abstractmethod

from app.core.enums import SignalType


class StrategyResult:
    def __init__(
        self,
        signal: SignalType,
        confidence: float = 0.0,
        metadata: dict | None = None,
        entry_price: float | None = None,
        stop_loss: float | None = None,
        take_profit: float | None = None,
    ):
        self.signal = signal
        self.confidence = confidence
        self.metadata = metadata or {}
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.take_profit = take_profit


class BaseStrategy(ABC):
    def __init__(self, name: str, params: dict | None = None):
        self.name = name
        self.params = params or {}

    @property
    def timeframe(self) -> str:
        """Primary timeframe this strategy trades on."""
        return self.params.get("timeframe", "15m")

    @property
    def required_timeframes(self) -> list[str]:
        """All timeframes needed. Override to request multiple TFs.
        First entry is the primary (signal) timeframe."""
        return [self.timeframe]

    @abstractmethod
    def analyze(self, candles: dict[str, list[dict]]) -> StrategyResult:
        """Analyze candles keyed by timeframe.
        Example: {'15m': [...], '1h': [...], '4h': [...]}
        """
        pass

    @property
    def description(self) -> str:
        return self.__doc__ or ""
