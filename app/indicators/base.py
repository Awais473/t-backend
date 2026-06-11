from abc import ABC, abstractmethod

import importlib
import inspect
import pkgutil


class IndicatorResult:
    def __init__(self, indicator: str, data: list[dict], params: dict | None = None):
        self.indicator = indicator
        self.data = data
        self.params = params or {}


_registry: dict[str, type["BaseIndicator"]] = {}
_discovered = False


def _ensure_discovered():
    global _discovered
    if _discovered:
        return
    _discovered = True
    import app.indicators as indicators_pkg

    for _importer, modname, _ispkg in pkgutil.iter_modules(indicators_pkg.__path__):
        if modname in ("base", "__init__"):
            continue
        module = importlib.import_module(f"app.indicators.{modname}")
        for name, cls in inspect.getmembers(module, inspect.isclass):
            if issubclass(cls, BaseIndicator) and cls is not BaseIndicator:
                register_indicator(cls().name, cls)


def register_indicator(name: str, cls: type["BaseIndicator"]):
    _registry[name] = cls


def get_indicator(name: str) -> type["BaseIndicator"] | None:
    _ensure_discovered()
    return _registry.get(name)


def list_indicators() -> list[dict]:
    _ensure_discovered()
    return [
        {"name": name, "description": cls().description}
        for name, cls in _registry.items()
    ]


class BaseIndicator(ABC):
    def __init__(self):
        self.name = ""

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @abstractmethod
    def calculate(self, candles: list[dict], **params) -> IndicatorResult:
        pass

    @staticmethod
    def _to_seconds(ts) -> int:
        if hasattr(ts, "timestamp"):
            return int(ts.timestamp())
        if isinstance(ts, (int, float)):
            return int(ts)
        from datetime import datetime
        return int(datetime.fromisoformat(ts).timestamp())
