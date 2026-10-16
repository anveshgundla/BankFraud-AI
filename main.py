
import sqlite3
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from database import (
    count_recent_transactions,
    save_transaction,
    get_transactions_by_account,
)
from fraud_rules import (
    check_transaction_amount,
    check_international_transaction,
    check_transaction_velocity,
)

app = FastAPI(
    title="BankFraud AI",
    description="AI-powered banking fraud investigation platform",
    version="1.0.0"
)


@app.get("/")
def home():
    return {
        "application": "BankFraud AI",
        "status": "running",
        "message": "BankFraud AI API is ready"
    }


class Transaction(BaseModel):
    transaction_id: str
    account_id: str
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    merchant: str
    location: str
    country: str = "US"
    transactions_last_10_minutes: int = Field(default=0, ge=0)


@app.post("/transactions/analyze")
def analyze_transaction(transaction: Transaction):
    amount_result = check_transaction_amount(transaction.amount)
    country_result = check_international_transaction(transaction.country)

    recent_count = count_recent_transactions(transaction.account_id)
    velocity_result = check_transaction_velocity(recent_count)

    risk_priority = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}

    risk_level = max(
        [
            amount_result["risk_level"],
            country_result["risk_level"],
            velocity_result["risk_level"]
        ],
        key=lambda level: risk_priority[level]
    )

    reason = "; ".join([
        amount_result["reason"],
        country_result["reason"],
        velocity_result["reason"]
    ])

    # Save transaction and handle duplicate transaction IDs.
    try:
        save_transaction(
            transaction_id=transaction.transaction_id,
            account_id=transaction.account_id,
            amount=transaction.amount,
            merchant=transaction.merchant,
            location=transaction.location,
            country=transaction.country,
            transaction_time=datetime.now(timezone.utc).isoformat()
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail="Transaction ID already exists"
        ) from exc

    return {
        "transaction_id": transaction.transaction_id,
        "account_id": transaction.account_id,
        "amount": transaction.amount,
        "merchant": transaction.merchant,
        "location": transaction.location,
        "risk_level": risk_level,
        "reason": reason
    }


@app.get("/transactions/{account_id}")
def get_account_transactions(account_id: str):
    transactions = get_transactions_by_account(account_id)

    return {
        "account_id": account_id,
        "total_transactions": len(transactions),
        "transactions": transactions
    }
def test_get_account_transactions():
    mock_transactions = [
        {
            "transaction_id": "TXN-1001",
            "account_id": "ACC-1001",
            "amount": "750",
            "merchant": "Grocery Store",
            "location": "Minnesota",
            "country": "US",
            "transaction_time": "2026-10-16T20:42:48+00:00"
        }
    ]

    with patch(
        "main.get_transactions_by_account",
        return_value=mock_transactions
    ):
        response = client.get("/transactions/ACC-1001")

    assert response.status_code == 200

    data = response.json()

    assert data["account_id"] == "ACC-1001"
    assert data["total_transactions"] == 1
    assert data["transactions"][0]["transaction_id"] == "TXN-1001"