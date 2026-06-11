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

    def fetch_klines_range(
        self,
        symbol: str,
        interval: str,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int = 1000,
    ) -> list[dict]:
        """Fetch candles in a time range with automatic pagination.
        Times are in seconds since epoch. Max 1000 per Binance API call,
        internally paginates for limit > 1000.
        """
        all_candles: list[dict] = []
        remaining = min(limit, 5000)
        batch_size = 1000

        params: dict = {
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": min(batch_size, remaining),
        }

        if end_time is not None:
            params["endTime"] = int(end_time * 1000)

        if start_time is not None:
            params["startTime"] = int(start_time * 1000)

        while remaining > 0:
            batch_limit = min(batch_size, remaining)
            params["limit"] = batch_limit

            url = f"{self.BASE_URL}/api/v3/klines"
            resp = httpx.get(url, params=params)
            resp.raise_for_status()
            batch = resp.json()
            if not batch:
                break

            parsed = self._parse_klines(batch, symbol, interval)
            all_candles.extend(parsed)
            remaining -= len(parsed)

            if len(batch) < batch_limit:
                break

            if end_time is not None:
                params["endTime"] = batch[0][0] - 1
                # don't paginate with both start+end, single range is enough
                if start_time is not None:
                    break
            elif start_time is not None:
                params["startTime"] = batch[-1][0] + 1
            else:
                break

        return all_candles

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
