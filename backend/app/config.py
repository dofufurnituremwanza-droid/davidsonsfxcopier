import os
import base64
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    APP_NAME: str = "DAVIDSONSFX TRADING COPIER"
    APP_VERSION: str = "1.0.0"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "davidsonsfx-super-secure-jwt-secret-key-2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # 32-byte url-safe base64 key for Fernet password encryption
    ENCRYPTION_KEY: str = os.getenv(
        "ENCRYPTION_KEY", 
        "cE9pU2t2R1ZaMTR3OHhUYk1WcWNYeURiTTRyTG9yZHM="
    )
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/davidsonsfx.db")
    
    # MT5 Defaults
    DEFAULT_MT5_PATH: str = os.getenv(
        "MT5_PATH", 
        r"C:\Program Files\MetaTrader 5\terminal64.exe"
    )
    
    # Server Host / Port
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()

