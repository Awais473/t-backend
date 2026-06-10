import json
from datetime import datetime

import httpx

from app.core.enums import DataSource, Timeframe


class BinanceCollector:
    BASE_URL = "https://api.binance.com"
    WS_URL = "wss://stream.binance.com:9443/ws"

    def fetch_klines(self, symbol: str, interval: str, limit: int = 100) -> list[dict]:
        url = f"{self.BASE_URL}/api/v3/klines"
        params = {"symbol": symbol.upper(), "interval": interval, "limit": limit}
        resp = httpx.get(url, params=params)
        resp.raise_for_status()
        return self._parse_klines(resp.json(), symbol, interval)

    def _parse_klines(self, klines: list, symbol: str, interval: str) -> list[dict]:
        parsed = []
        for k in klines:
            parsed.append({
                "symbol": symbol,
                "timeframe": interval,
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
                "timestamp": datetime.fromtimestamp(k[0] / 1000),
            })
        return parsed

    def get_ws_stream_name(self, symbol: str, interval: str) -> str:
        return f"{symbol.lower()}@kline_{interval}"

    def parse_ws_message(self, msg: str) -> dict | None:
        data = json.loads(msg)
        k = data.get("k")
        if not k:
            return None
        return {
            "symbol": k["s"],
            "timeframe": k["i"],
            "open": float(k["o"]),
            "high": float(k["h"]),
            "low": float(k["l"]),
            "close": float(k["c"]),
            "volume": float(k["v"]),
            "timestamp": datetime.fromtimestamp(k["t"] / 1000),
        }
