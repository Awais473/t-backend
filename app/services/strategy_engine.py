import importlib
import inspect
import pkgutil
from datetime import datetime

import httpx

from app.strategies.base import BaseStrategy, StrategyResult

_registry: dict[str, type[BaseStrategy]] = {}


def register_strategy(name: str, cls: type[BaseStrategy]):
    _registry[name] = cls


def get_strategy(name: str, params: dict | None = None) -> BaseStrategy | None:
    cls = _registry.get(name)
    if not cls:
        return None
    return cls(params)


def list_strategies() -> list[dict]:
    return [
        {"name": name, "description": cls().description}
        for name, cls in _registry.items()
    ]


def _discover_strategies():
    import app.strategies as strategies_pkg

    for _importer, modname, _ispkg in pkgutil.iter_modules(strategies_pkg.__path__):
        if modname in ("base", "__init__"):
            continue
        module = importlib.import_module(f"app.strategies.{modname}")
        for name, cls in inspect.getmembers(module, inspect.isclass):
            if issubclass(cls, BaseStrategy) and cls is not BaseStrategy:
                register_strategy(cls().name, cls)


_discover_strategies()


def get_candles_as_dicts(symbol: str, timeframe: str, limit: int = 200) -> list[dict]:
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol.upper(), "interval": timeframe, "limit": limit}
    resp = httpx.get(url, params=params)
    resp.raise_for_status()
    klines = []
    for k in resp.json():
        klines.append({
            "open": float(k[1]),
            "high": float(k[2]),
            "low": float(k[3]),
            "close": float(k[4]),
            "volume": float(k[5]),
            "timestamp": datetime.fromtimestamp(k[0] / 1000).isoformat(),
        })
    return klines


def get_candles_for_strategy(strategy: BaseStrategy, symbol: str) -> dict[str, list[dict]]:
    """Fetch all required timeframes for a strategy."""
    result = {}
    for tf in strategy.required_timeframes:
        result[tf] = get_candles_as_dicts(symbol, tf, 200)
    return result
