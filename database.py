
import sqlite3
from datetime import datetime, timedelta, timezone

DATABASE_NAME = "bankfraud.db"


def get_connection():
    connection = sqlite3.connect(DATABASE_NAME)
    return connection


def create_transactions_table():
    connection = get_connection()

    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                amount TEXT NOT NULL,
                merchant TEXT NOT NULL,
                location TEXT NOT NULL,
                country TEXT NOT NULL,
                transaction_time TEXT NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_transactions_account_id
            ON transactions (account_id)
            """
        )

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


def count_recent_transactions(account_id: str) -> int:
    current_time = datetime.now(timezone.utc)
    ten_minutes_ago = current_time - timedelta(minutes=10)

    connection = get_connection()

    try:
        result = connection.execute(
            """
            SELECT COUNT(*)
            FROM transactions
            WHERE account_id = ?
              AND julianday(transaction_time) >= julianday(?)
              AND julianday(transaction_time) <= julianday(?)
            """,
            (
                account_id,
                ten_minutes_ago.isoformat(),
                current_time.isoformat()
            )
        ).fetchone()

        return result[0]
    finally:
        connection.close()


def get_transactions_by_account(account_id: str):
    connection = get_connection()
    connection.row_factory = sqlite3.Row

    try:
        rows = connection.execute(
            """
            SELECT
                transaction_id,
                account_id,
                amount,
                merchant,
                location,
                country,
                transaction_time
            FROM transactions
            WHERE account_id = ?
            ORDER BY transaction_time DESC
            """,
            (account_id,)
        ).fetchall()

        return [dict(row) for row in rows]
    finally:
        connection.close()
