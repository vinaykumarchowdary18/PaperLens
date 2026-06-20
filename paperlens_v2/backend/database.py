import aiosqlite
import os

DB_PATH = os.getenv("DB_PATH", "paperlens.db")

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id          TEXT PRIMARY KEY,
                email       TEXT UNIQUE NOT NULL,
                name        TEXT,
                credits     INTEGER DEFAULT 1,
                free_used   INTEGER DEFAULT 0,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id              TEXT PRIMARY KEY,
                user_id         TEXT NOT NULL,
                filename        TEXT,
                status          TEXT DEFAULT 'pending',
                ai_score        REAL,
                plag_score      REAL,
                word_count      INTEGER,
                result_json     TEXT,
                created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id              TEXT PRIMARY KEY,
                user_id         TEXT NOT NULL,
                payment_ref     TEXT,
                amount_paise    INTEGER,
                credits         INTEGER,
                status          TEXT DEFAULT 'pending',
                created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        await db.commit()

async def get_db():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db
