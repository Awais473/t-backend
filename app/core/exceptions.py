class TradingBotException(Exception):
    pass


class StrategyNotFoundError(TradingBotException):
    def __init__(self, name: str):
        super().__init__(f"Strategy '{name}' not found")


class InvalidCandleDataError(TradingBotException):
    def __init__(self, msg: str = "Invalid candle data"):
        super().__init__(msg)


class InsufficientDataError(TradingBotException):
    def __init__(self, msg: str = "Insufficient historical data"):
        super().__init__(msg)
