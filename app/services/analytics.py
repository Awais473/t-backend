from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.trade import Trade


def _filter_by_days(query, days: int | None):
    if days is not None:
        cutoff = datetime.now(timezone.utc)
        return query.filter(Trade.entry_time >= cutoff)
    return query


def compute_trade_metrics(db: Session, days: int | None = None) -> dict:
    query = _filter_by_days(db.query(Trade), days) if days is not None else db.query(Trade)
    trades = query.all()

    total = len(trades)
    closed = [t for t in trades if t.status == "CLOSED"]
    winning = [t for t in closed if t.pnl and t.pnl > 0]
    losing = [t for t in closed if t.pnl and t.pnl <= 0]

    total_pnl = sum(t.pnl or 0 for t in closed)
    win_rate = len(winning) / len(closed) * 100 if closed else 0
    gross_profit = sum(t.pnl for t in winning) if winning else 0
    gross_loss = abs(sum(t.pnl for t in losing)) if losing else 0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
    avg_rr = (
        sum(t.rr_ratio or 0 for t in closed if t.rr_ratio)
        / len([t for t in closed if t.rr_ratio])
        if any(t.rr_ratio for t in closed)
        else 0
    )

    best_trade = max(closed, key=lambda t: t.pnl or 0, default=None)
    worst_trade = min(closed, key=lambda t: t.pnl or 0, default=None)

    consecutive_wins = _max_consecutive(closed, lambda t: t.pnl > 0 if t.pnl else False)
    consecutive_losses = _max_consecutive(closed, lambda t: t.pnl <= 0 if t.pnl else True)

    return {
        "total_trades": total,
        "closed_trades": len(closed),
        "winning_trades": len(winning),
        "losing_trades": len(losing),
        "total_pnl": round(total_pnl, 2),
        "win_rate": round(win_rate, 2),
        "profit_factor": round(profit_factor, 2),
        "avg_rr": round(avg_rr, 2),
        "consecutive_wins": consecutive_wins,
        "consecutive_losses": consecutive_losses,
        "best_trade": {"pnl": round(best_trade.pnl, 2), "symbol": best_trade.symbol} if best_trade else None,
        "worst_trade": {"pnl": round(worst_trade.pnl, 2), "symbol": worst_trade.symbol} if worst_trade else None,
    }


def rank_strategies(db: Session, days: int | None = None) -> list[dict]:
    query = _filter_by_days(db.query(Trade), days) if days is not None else db.query(Trade)
    trades = query.all()
    strategy_names = set(t.strategy_name for t in trades)

    rankings = []
    for name in strategy_names:
        strategy_trades = [t for t in trades if t.strategy_name == name]
        closed = [t for t in strategy_trades if t.status == "CLOSED"]
        winning = [t for t in closed if t.pnl and t.pnl > 0]
        losing = [t for t in closed if t.pnl and t.pnl <= 0]

        win_rate = len(winning) / len(closed) * 100 if closed else 0
        gross_profit = sum(t.pnl for t in winning) if winning else 0
        gross_loss = abs(sum(t.pnl for t in losing)) if losing else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
        total_pnl = sum(t.pnl or 0 for t in closed)
        max_dd = _compute_max_drawdown(closed)

        returns = [t.pnl_percent or 0 for t in closed if t.pnl_percent is not None]
        sharpe = _compute_sharpe(returns)

        avg_rr = (
            sum(t.rr_ratio or 0 for t in closed if t.rr_ratio)
            / len([t for t in closed if t.rr_ratio])
            if any(t.rr_ratio for t in closed)
            else 0
        )
        con_wins = _max_consecutive(closed, lambda t: t.pnl > 0 if t.pnl else False)
        con_losses = _max_consecutive(closed, lambda t: t.pnl <= 0 if t.pnl else True)

        score = win_rate * 0.3 + min(profit_factor, 10) * 10 * 0.3 + min(sharpe, 3) * 33.3 * 0.4

        rankings.append({
            "name": name,
            "win_rate": round(win_rate, 2),
            "profit_factor": round(profit_factor, 2),
            "total_pnl": round(total_pnl, 2),
            "max_drawdown": round(max_dd, 2),
            "sharpe_ratio": round(sharpe, 2),
            "score": round(score, 2),
            "avg_rr": round(avg_rr, 2),
            "consecutive_wins": con_wins,
            "consecutive_losses": con_losses,
            "total_trades": len(closed),
        })

    rankings.sort(key=lambda r: r["score"], reverse=True)
    for i, r in enumerate(rankings):
        r["rank"] = i + 1

    return rankings


def _max_consecutive(trades: list, pred) -> int:
    best = cur = 0
    for t in trades:
        if pred(t):
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def _compute_max_drawdown(trades: list) -> float:
    if not trades:
        return 0
    peak = float("-inf")
    max_dd = 0
    for t in trades:
        if t.pnl is not None:
            peak = max(peak, t.pnl)
            dd = peak - t.pnl if peak > t.pnl else 0
            max_dd = max(max_dd, dd)
    return max_dd


def _compute_sharpe(returns: list[float], risk_free_rate: float = 0.02) -> float:
    if len(returns) < 2:
        return 0
    import statistics
    mean = statistics.mean(returns)
    std = statistics.stdev(returns)
    if std == 0:
        return 0
    return (mean - risk_free_rate / 252) / std * (252 ** 0.5)
