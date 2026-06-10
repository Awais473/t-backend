"""In-memory store for user-activated strategy subscriptions."""

from pydantic import BaseModel


class ActiveStrategy(BaseModel):
    strategy_name: str
    symbol: str
    primary_timeframe: str

    @property
    def timeframes(self) -> list[str]:
        """Timeframes this strategy instance needs to process.
        Determined by the strategy's required_timeframes.
        Imported lazily to avoid circular imports."""
        from app.services.strategy_engine import get_strategy
        s = get_strategy(self.strategy_name, {"timeframe": self.primary_timeframe})
        if s:
            return s.required_timeframes
        return [self.primary_timeframe]


_store: dict[str, ActiveStrategy] = {}


def _key(strategy_name: str, symbol: str) -> str:
    return f"{strategy_name}:{symbol}"


def activate(name: str, symbol: str, primary_timeframe: str) -> ActiveStrategy:
    sub = ActiveStrategy(strategy_name=name, symbol=symbol, primary_timeframe=primary_timeframe)
    _store[_key(name, symbol)] = sub
    return sub


def deactivate(name: str, symbol: str) -> bool:
    return _store.pop(_key(name, symbol), None) is not None


def is_active(name: str, symbol: str) -> bool:
    return _key(name, symbol) in _store


def list_active() -> list[ActiveStrategy]:
    return list(_store.values())


def match_active(symbol: str) -> list[ActiveStrategy]:
    """Return all active strategies for a given symbol."""
    return [s for s in _store.values() if s.symbol == symbol]
