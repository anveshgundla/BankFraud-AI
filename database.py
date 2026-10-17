
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


def get_transactions_by_account(
    account_id: str,
    start_date: str | None = None,
    end_date: str | None = None
):
    connection = get_connection()
    connection.row_factory = sqlite3.Row

    try:
        query = """
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
        """

        parameters = [account_id]

        if start_date is not None:
            query += " AND date(transaction_time) >= date(?)"
            parameters.append(start_date)

        if end_date is not None:
            query += " AND date(transaction_time) <= date(?)"
            parameters.append(end_date)

        query += " ORDER BY transaction_time DESC"

        rows = connection.execute(
            query,
            parameters
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()


# Create the table for storing fraud alerts.
def create_fraud_alerts_table():
    connection = get_connection()

    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS fraud_alerts (
                transaction_id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                risk_score INTEGER NOT NULL,
                reason TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'OPEN',
                created_at TEXT NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_fraud_alerts_account_id
            ON fraud_alerts (account_id)
            """
        )

        connection.commit()

    finally:
        connection.close()


def save_fraud_alert(alert: dict):
    connection = get_connection()

    try:
        connection.execute(
            """
            INSERT INTO fraud_alerts (
                transaction_id,
                account_id,
                risk_level,
                risk_score,
                reason,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                alert["transaction_id"],
                alert["account_id"],
                alert["risk_level"],
                alert["risk_score"],
                alert["reason"],
                alert["status"],
                alert["created_at"]
            )
        )

        connection.commit()

    finally:
        connection.close()


def get_fraud_alerts():
    connection = get_connection()
    connection.row_factory = sqlite3.Row

    try:
        rows = connection.execute(
            """
            SELECT
                transaction_id,
                account_id,
                risk_level,
                risk_score,
                reason,
                status,
                created_at
            FROM fraud_alerts
            ORDER BY created_at DESC
            """
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()


def get_dashboard_summary():
    connection = get_connection()

    try:
        result = connection.execute(
            """
            SELECT
                COUNT(*) AS total_alerts,

                COUNT(
                    CASE
                        WHEN status = 'OPEN' THEN 1
                    END
                ) AS open_alerts,

                COUNT(
                    CASE
                        WHEN risk_level = 'HIGH' THEN 1
                    END
                ) AS high_risk_alerts,

                COALESCE(
                    ROUND(AVG(risk_score), 2),
                    0
                ) AS average_risk_score

            FROM fraud_alerts
            """
        ).fetchone()

        return {
            "total_alerts": result[0],
            "open_alerts": result[1],
            "high_risk_alerts": result[2],
            "average_risk_score": result[3]
        }

    finally:
        connection.close()


# Update the investigation status of an existing fraud alert.
def update_fraud_alert_status(
    transaction_id: str,
    new_status: str
) -> dict | None:

    allowed_statuses = {
        "OPEN",
        "UNDER_REVIEW",
        "RESOLVED"
    }

    if new_status not in allowed_statuses:
        raise ValueError(
            "Invalid status. Allowed values: "
            "OPEN, UNDER_REVIEW, RESOLVED"
        )

    connection = get_connection()
    connection.row_factory = sqlite3.Row

    try:
        cursor = connection.execute(
            """
            UPDATE fraud_alerts
            SET status = ?
            WHERE transaction_id = ?
            """,
            (new_status, transaction_id)
        )

        if cursor.rowcount == 0:
            return None

        connection.commit()

        row = connection.execute(
            """
            SELECT
                transaction_id,
                account_id,
                risk_level,
                risk_score,
                reason,
                status,
                created_at
            FROM fraud_alerts
            WHERE transaction_id = ?
            """,
            (transaction_id,)
        ).fetchone()

        return dict(row) if row else None

    finally:
        connection.close()
