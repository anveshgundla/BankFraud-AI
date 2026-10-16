
from decimal import Decimal

from fastapi import FastAPI
from pydantic import BaseModel, Field

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
    velocity_result = check_transaction_velocity(
        transaction.transactions_last_10_minutes
    )

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

    return {
        "transaction_id": transaction.transaction_id,
        "account_id": transaction.account_id,
        "amount": transaction.amount,
        "merchant": transaction.merchant,
        "location": transaction.location,
        "risk_level": risk_level,
        "reason": reason
    }
