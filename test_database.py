from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import sqlite3

from database import count_recent_transactions


def test_recent_transaction_count(tmp_path):
    test_db = tmp_path / "test_bankfraud.db"

    connection = sqlite3.connect(test_db)
    try:
        connection.execute("""
            CREATE TABLE transactions (
                transaction_id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                transaction_time TEXT NOT NULL
            )
        """)

        now = datetime.now(timezone.utc)

        transactions = [
            ("TXN-1", "ACC-1001", (now - timedelta(minutes=2)).isoformat()),
            ("TXN-2", "ACC-1001", (now - timedelta(minutes=5)).isoformat()),
            ("TXN-3", "ACC-1001", (now - timedelta(minutes=15)).isoformat()),
            ("TXN-4", "ACC-OTHER", (now - timedelta(minutes=1)).isoformat()),
        ]

        connection.executemany(
            "INSERT INTO transactions VALUES (?, ?, ?)",
            transactions
        )
        connection.commit()
    finally:
        connection.close()

    with patch("database.DATABASE_NAME", str(test_db)):
        result = count_recent_transactions("ACC-1001")

    assert result == 2