from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import sqlite3

from database import count_recent_transactions
from database import get_transactions_by_account


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

def test_get_transactions_by_account_date_filter(tmp_path):
    import sqlite3
    from unittest.mock import patch

    test_db = tmp_path / "test_transactions.db"

    with sqlite3.connect(test_db) as connection:
        connection.execute("""
            CREATE TABLE transactions (
                transaction_id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                amount TEXT NOT NULL,
                merchant TEXT NOT NULL,
                location TEXT NOT NULL,
                country TEXT NOT NULL,
                transaction_time TEXT NOT NULL
            )
        """)

        transactions = [
            ("TXN-001", "ACC-1001", "100", "Store A", "MN", "US", "2026-10-10T10:00:00+00:00"),
            ("TXN-002", "ACC-1001", "200", "Store B", "MN", "US", "2026-10-15T10:00:00+00:00"),
            ("TXN-003", "ACC-1001", "300", "Store C", "MN", "US", "2026-10-20T10:00:00+00:00"),
        ]

        connection.executemany(
            "INSERT INTO transactions VALUES (?, ?, ?, ?, ?, ?, ?)",
            transactions
        )

    with patch("database.DATABASE_NAME", str(test_db)):
        result = get_transactions_by_account(
            "ACC-1001",
            start_date="2026-10-12",
            end_date="2026-10-18"
        )

    assert len(result) == 1
    assert result[0]["transaction_id"] == "TXN-002"
