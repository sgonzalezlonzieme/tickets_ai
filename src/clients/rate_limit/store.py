from contextlib import closing
from pathlib import Path
import sqlite3


class RateLimitStore:
    WINDOW_SECONDS = 60.0

    def __init__(self, path: Path):
        self._path = path

    def reserve(self, provider: str, limit: int, now: float) -> float:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self._path, timeout=10)) as connection, connection:
            connection.execute("CREATE TABLE IF NOT EXISTS requests (provider TEXT, sent_at REAL)")
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "DELETE FROM requests WHERE sent_at <= ?", (now - self.WINDOW_SECONDS,),
            )
            count, oldest = connection.execute(
                "SELECT COUNT(*), MIN(sent_at) FROM requests WHERE provider = ?", (provider,),
            ).fetchone()
            if count < limit:
                connection.execute("INSERT INTO requests VALUES (?, ?)", (provider, now))
                return 0.0
            return max(0.0, oldest + self.WINDOW_SECONDS - now)
