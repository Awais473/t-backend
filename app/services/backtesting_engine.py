from datetime import datetime

from app.services.strategy_engine import get_candles_as_dicts, get_strategy


class BacktestTrade:
    def __init__(self):
        self.entry_time: datetime | None = None
        self.exit_time: datetime | None = None
        self.entry_price: float = 0.0
        self.exit_price: float = 0.0
        self.side: str = ""
        self.quantity: float = 0.0
        self.pnl: float = 0.0
        self.pnl_percent: float = 0.0
        self.status: str = "OPEN"


class BacktestResult:
    def __init__(self):
        self.trades: list[BacktestTrade] = []
        self.equity_curve: list[float] = []
        self.total_pnl: float = 0.0
        self.winning_trades: int = 0
        self.losing_trades: int = 0
        self.max_drawdown: float = 0.0
        self.profit_factor: float = 0.0
        self.sharpe_ratio: float = 0.0


class BacktestingEngine:
    def __init__(self, initial_capital: float = 10000.0):
        self.initial_capital = initial_capital
        self.capital = initial_capital

    def run(self, strategy_name: str, symbol: str, timeframe: str, limit: int = 500) -> BacktestResult:
        candles = get_candles_as_dicts(symbol, timeframe, limit)
        strategy = get_strategy(strategy_name)
        if not strategy or len(candles) < 50:
            return BacktestResult()

        result = BacktestResult()
        position: BacktestTrade | None = None
        equity = [self.capital]

        for i in range(50, len(candles)):
            window = candles[:i]
            curr = candles[i]
            res = strategy.analyze({timeframe: window})

            if position is None and res.signal.value == "BUY":
                position = BacktestTrade()
                position.entry_time = datetime.fromisoformat(curr["timestamp"])
                position.entry_price = curr["close"]
                position.side = "LONG"
                position.quantity = self.capital / curr["close"]

            elif position is not None and position.status == "OPEN":
                exit_signal = (
                    (position.side == "LONG" and res.signal.value == "SELL")
                )
                if exit_signal or i == len(candles) - 1:
                    position.exit_time = datetime.fromisoformat(curr["timestamp"])
                    position.exit_price = curr["close"]
                    position.pnl = (position.exit_price - position.entry_price) * position.quantity
                    position.pnl_percent = (position.exit_price - position.entry_price) / position.entry_price * 100
                    position.status = "CLOSED"
                    self.capital += position.pnl
                    equity.append(self.capital)
                    if position.pnl > 0:
                        result.winning_trades += 1
                    else:
                        result.losing_trades += 1
                    result.trades.append(position)
                    position = None

        result.total_pnl = self.capital - self.initial_capital
        result.equity_curve = equity
        peak = max(equity)
        current = equity[-1]
        result.max_drawdown = (peak - current) / peak * 100 if peak > 0 else 0

        total_wins = sum(t.pnl for t in result.trades if t.pnl > 0)
        total_losses = abs(sum(t.pnl for t in result.trades if t.pnl < 0))
        result.profit_factor = total_wins / total_losses if total_losses > 0 else float("inf")

        returns = [
            (equity[i] - equity[i - 1]) / equity[i - 1]
            for i in range(1, len(equity))
            if equity[i - 1] > 0
        ]
        if returns and len(returns) > 1:
            avg_return = sum(returns) / len(returns)
            std = (sum((r - avg_return) ** 2 for r in returns) / (len(returns) - 1)) ** 0.5
            result.sharpe_ratio = avg_return / std * (252 ** 0.5) if std > 0 else 0

        return result
