from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./trading_bot.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    BINANCE_API_KEY: str = ""
    BINANCE_SECRET_KEY: str = ""
    BINANCE_WS_URL: str = "wss://stream.binance.com:9443/ws"
    CORS_ORIGINS: str = "http://localhost:5173"
    WS_HEARTBEAT_INTERVAL: int = 30

    class Config:
        env_file = ".env"


settings = Settings()
