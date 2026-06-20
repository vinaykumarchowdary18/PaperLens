from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # App
    APP_ENV: str = "development"
    SECRET_KEY: str = "change-this-in-production-min-32-chars"
    FRONTEND_URL: str = "http://localhost:5173"
    BACKEND_URL: str = "http://localhost:8000"

    # DB
    DB_PATH: str = "paperlens.db"

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # ── AI Detection Agents (add as many as you can — they cover each other) ──
    GPTZERO_API_KEY: str = ""    # https://gptzero.me/api         — 10k words/day free
    SAPLING_API_KEY: str = ""    # https://sapling.ai/settings    — 50 req/day free
    ZEROGPT_API_KEY: str = ""    # https://zerogpt.com/api        — free, no key needed but key gives more
    WRITER_API_KEY: str  = ""    # https://dev.writer.com         — 100 req/day free

    # ── Plagiarism Agents (all free, no key needed except CORE for higher limits) ──
    CORE_API_KEY: str = ""       # https://core.ac.uk/services/api — optional, free key raises limits

    # ── Cashfree Payments ─────────────────────────────────────────────────────
    CASHFREE_APP_ID: str = ""
    CASHFREE_SECRET_KEY: str = ""

    class Config:
        env_file = ".env"

@lru_cache
def get_settings() -> Settings:
    return Settings()
