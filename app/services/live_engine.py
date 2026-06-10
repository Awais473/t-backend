import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.signal import Signal
from app.models.trade import Trade
from app.models.strategy_metrics import StrategyMetrics
from app.services.active_strategies import match_active
from app.services.strategy_engine import get_candles_for_strategy, get_strategy

RESULT_MAP = {"BUY": "WIN", "SELL": "LOSS"}


class LiveSignalEngine:
    def __init__(self, db: Session):
        self.db = db

    async def process_candle(self, symbol: str, timeframe: str, candle: dict) -> dict | None:
        active_subs = match_active(symbol)
        broadcasts = []

        for sub in active_subs:
            if timeframe not in sub.timeframes:
                continue

            strategy = get_strategy(sub.strategy_name, {"timeframe": sub.primary_timeframe})
            if not strategy:
                continue

            all_candles = get_candles_for_strategy(strategy, symbol)
            primary_data = all_candles.get(strategy.timeframe, [])
            if not primary_data:
                continue

            result = strategy.analyze(all_candles)
            last = primary_data[-1]

            signal_payload = {
                "type": "signal",
                "strategy": strategy.name,
                "symbol": symbol,
                "timeframe": strategy.timeframe,
                "signal": result.signal.value,
                "price": last["close"],
                "confidence": result.confidence,
                "entry_price": result.entry_price,
                "stop_loss": result.stop_loss,
                "take_profit": result.take_profit,
                "metadata": result.metadata,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            if result.signal.value != "HOLD":
                signal_record = Signal(
                    strategy_name=strategy.name,
                    symbol=symbol,
                    timeframe=strategy.timeframe,
                    signal=result.signal.value,
                    price=last["close"],
                    entry_price=result.entry_price,
                    stop_loss=result.stop_loss,
                    take_profit=result.take_profit,
                    confidence=result.confidence,
                    extra_data=json.dumps(result.metadata) if result.metadata else None,
                    timestamp=datetime.now(timezone.utc),
                )
                self.db.add(signal_record)
                self.db.flush()

                trade_result = self._manage_trade(strategy, result, last, signal_record)
                if trade_result:
                    signal_payload["trade"] = trade_result
                    self._update_metrics(strategy.name, symbol, strategy.timeframe, trade_result)

            broadcasts.append(signal_payload)

        self.db.commit()
        return broadcasts

    def _manage_trade(self, strategy, result, candle: dict, signal_record: Signal) -> dict | None:
        now = datetime.now(timezone.utc)
        signal = result.signal.value
        price = candle["close"]

        open_trade = (
            self.db.query(Trade)
            .filter(
                Trade.strategy_name == strategy.name,
                Trade.symbol == signal_record.symbol,
                Trade.status == "OPEN",
            )
            .first()
        )

        is_long = signal == "BUY"
        is_short = signal == "SELL"

        if open_trade:
            should_close = (open_trade.side == "LONG" and is_short) or (open_trade.side == "SHORT" and is_long) or signal == "EXIT"
            if should_close:
                open_trade.exit_price = price
                open_trade.exit_time = now
                open_trade.status = "CLOSED"
                open_trade.pnl = (price - open_trade.entry_price) * open_trade.quantity if open_trade.side == "LONG" else (open_trade.entry_price - price) * open_trade.quantity
                open_trade.pnl_percent = ((price / open_trade.entry_price) - 1) * 100 if open_trade.side == "LONG" else ((open_trade.entry_price / price) - 1) * 100
                open_trade.duration_minutes = int((now - open_trade.entry_time).total_seconds() / 60)
                open_trade.result = "WIN" if (open_trade.pnl or 0) > 0 else "LOSS"
                if open_trade.stop_loss:
                    risk = abs(open_trade.entry_price - open_trade.stop_loss)
                    reward = abs(price - open_trade.entry_price)
                    open_trade.rr_ratio = round(reward / risk, 2) if risk > 0 else None
                self.db.flush()
                return {
                    "action": "close",
                    "trade_id": open_trade.id,
                    "side": open_trade.side,
                    "entry_price": open_trade.entry_price,
                    "exit_price": price,
                    "pnl": open_trade.pnl,
                    "pnl_percent": open_trade.pnl_percent,
                    "duration_minutes": open_trade.duration_minutes,
                    "rr_ratio": open_trade.rr_ratio,
                    "result": open_trade.result,
                }
            return None

        if is_long or is_short:
            side = "LONG" if is_long else "SHORT"
            trade = Trade(
                strategy_name=strategy.name,
                symbol=signal_record.symbol,
                timeframe=strategy.timeframe,
                side=side,
                entry_price=result.entry_price or price,
                stop_loss=result.stop_loss,
                take_profit=result.take_profit,
                quantity=1.0,
                entry_time=now,
                status="OPEN",
            )
            self.db.add(trade)
            self.db.flush()
            return {
                "action": "open",
                "trade_id": trade.id,
                "side": side,
                "entry_price": trade.entry_price,
                "stop_loss": trade.stop_loss,
                "take_profit": trade.take_profit,
            }

        return None

    def _update_metrics(self, strategy_name: str, symbol: str, timeframe: str, trade_result: dict):
        metrics = (
            self.db.query(StrategyMetrics)
            .filter(
                StrategyMetrics.strategy_name == strategy_name,
                StrategyMetrics.symbol == symbol,
                StrategyMetrics.timeframe == timeframe,
            )
            .first()
        )

        if not metrics:
            metrics = StrategyMetrics(
                strategy_name=strategy_name,
                symbol=symbol,
                timeframe=timeframe,
            )
            self.db.add(metrics)
            self.db.flush()

        closed = (
            self.db.query(Trade)
            .filter(
                Trade.strategy_name == strategy_name,
                Trade.symbol == symbol,
                Trade.status == "CLOSED",
            )
            .all()
        )

        total = len(closed)
        wins = [t for t in closed if t.result == "WIN"]
        losses = [t for t in closed if t.result == "LOSS"]

        metrics.total_trades = total
        metrics.winning_trades = len(wins)
        metrics.losing_trades = len(losses)
        metrics.win_rate = len(wins) / total * 100 if total > 0 else 0

        gross_profit = sum(t.pnl or 0 for t in wins)
        gross_loss = abs(sum(t.pnl or 0 for t in losses))
        metrics.profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        rrs = [t.rr_ratio for t in closed if t.rr_ratio is not None]
        metrics.average_rr = sum(rrs) / len(rrs) if rrs else 0

        peak = float("-inf")
        dd = 0
        eq = 0
        for t in closed:
            eq += t.pnl or 0
            peak = max(peak, eq)
            dd = max(dd, peak - eq)
        metrics.max_drawdown = dd

        metrics.net_profit = sum(t.pnl or 0 for t in closed)

        returns = [t.pnl_percent or 0 for t in closed]
        if len(returns) > 1:
            avg = sum(returns) / len(returns)
            std = (sum((r - avg) ** 2 for r in returns) / (len(returns) - 1)) ** 0.5
            metrics.sharpe_ratio = avg / std * (252 ** 0.5) if std > 0 else 0

        con_wins = con_losses = 0
        best_w = best_l = 0
        for t in closed:
            if t.result == "WIN":
                con_wins += 1
                con_losses = 0
                best_w = max(best_w, con_wins)
            elif t.result == "LOSS":
                con_losses += 1
                con_wins = 0
                best_l = max(best_l, con_losses)
        metrics.consecutive_wins = best_w
        metrics.consecutive_losses = best_l

        metrics.last_trade_result = trade_result.get("result")
        self.db.flush()
