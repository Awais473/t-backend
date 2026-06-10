import asyncio
import json
from datetime import datetime

import websockets

from app.config import settings
from app.database import SessionLocal
from app.services.live_engine import LiveSignalEngine
from app.api.ws import manager as ws_manager


def _parse_kline(k: dict) -> dict:
    return {
        "symbol": k["s"],
        "timeframe": k["i"],
        "open": float(k["o"]),
        "high": float(k["h"]),
        "low": float(k["l"]),
        "close": float(k["c"]),
        "volume": float(k["v"]),
        "timestamp": k["t"],
    }


class BinanceStreamManager:
    def __init__(self):
        self._running = False
        self._tasks: list[asyncio.Task] = []

    async def start(self, symbols: list[str] = None, intervals: list[str] = None):
        if self._running:
            return
        self._running = True
        symbols = symbols or ["btcusdt", "ethusdt"]
        intervals = intervals or ["1m", "5m", "15m", "30m", "1h"]

        for symbol in symbols:
            for interval in intervals:
                stream_name = f"{symbol}@kline_{interval}"
                task = asyncio.create_task(self._listen(stream_name))
                self._tasks.append(task)

    async def stop(self):
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    async def _listen(self, stream_name: str):
        url = f"{settings.BINANCE_WS_URL}/{stream_name}"
        while self._running:
            try:
                async with websockets.connect(url) as ws:
                    while self._running:
                        msg = await ws.recv()
                        if isinstance(msg, bytes):
                            msg = msg.decode()
                        data = json.loads(msg)
                        k = data.get("k")
                        if not k:
                            continue
                        candle = _parse_kline(k)
                        await self._handle_candle(candle, is_final=k["x"])
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(5)

    async def _handle_candle(self, candle: dict, is_final: bool):
        ts = datetime.fromtimestamp(candle["timestamp"] / 1000)
        candle_payload = {
            "type": "candle",
            "symbol": candle["symbol"],
            "timeframe": candle["timeframe"],
            "open": candle["open"],
            "high": candle["high"],
            "low": candle["low"],
            "close": candle["close"],
            "volume": candle["volume"],
            "timestamp": ts.isoformat(),
            "is_final": is_final,
        }
        await ws_manager.broadcast(candle_payload)

        if is_final:
            db = SessionLocal()
            try:
                engine = LiveSignalEngine(db)
                signals = await engine.process_candle(
                    candle["symbol"], candle["timeframe"], candle
                )
                if signals:
                    for sig in signals:
                        await ws_manager.broadcast(sig)
            finally:
                db.close()


stream_manager = BinanceStreamManager()
