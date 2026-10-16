import sqlite3

DATABASE_NAME = "bankfraud.db"


def get_connection():
    connection = sqlite3.connect(DATABASE_NAME)
    return connection


def create_transactions_table():
    connection = get_connection()
    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                amount TEXT NOT NULL,
                merchant TEXT NOT NULL,
                location TEXT NOT NULL,
                country TEXT NOT NULL,
                transaction_time TEXT NOT NULL
            )
        """)
        connection.commit()
    finally:
        connection.close()
def save_transaction(
    transaction_id,
    account_id,
    amount,
    merchant,
    location,
    country,
    transaction_time
):
    connection = get_connection()

    try:
        connection.execute(
            """
            INSERT INTO transactions (
                transaction_id,
                account_id,
                amount,
                merchant,
                location,
                country,
                transaction_time
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                transaction_id,
                account_id,
                str(amount),
                merchant,
                location,
                country,
                transaction_time
            )
        )
        connection.commit()
    finally:
        connection.close()

from datetime import datetime, timedelta, timezone


def count_recent_transactions(account_id: str) -> int:
    current_time = datetime.now(timezone.utc)
    ten_minutes_ago = current_time - timedelta(minutes=10)

    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT transaction_time
            FROM transactions
            WHERE account_id = ?
            """,
            (account_id,)
        ).fetchall()
    finally:
        connection.close()

    count = 0

    for row in rows:
        transaction_time = datetime.fromisoformat(row[0])

        if ten_minutes_ago <= transaction_time <= current_time:
            count += 1

    return count