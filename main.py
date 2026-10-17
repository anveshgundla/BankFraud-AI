
import sqlite3
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from database import (
    count_recent_transactions,
    save_transaction,
    get_transactions_by_account,
    save_fraud_alert,
    get_fraud_alerts,
    get_dashboard_summary,
    update_fraud_alert_status,
)

from fraud_rules import (
    check_transaction_amount,
    check_international_transaction,
    check_transaction_velocity,
)

from fraud_alerts import (
    calculate_risk_score,
    create_fraud_alert,
)

from fraud_agent import fraud_investigation_agent


app = FastAPI(
    title="BankFraud AI",
    description="AI-powered banking fraud investigation platform",
    version="1.0.0"
)


# Allow the React frontend to access FastAPI.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type"],
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
    amount: Decimal = Field(
        gt=0,
        max_digits=12,
        decimal_places=2
    )
    merchant: str
    location: str
    country: str = "US"
    transactions_last_10_minutes: int = Field(
        default=0,
        ge=0
    )


@app.post("/transactions/analyze")
def analyze_transaction(transaction: Transaction):

    amount_result = check_transaction_amount(
        transaction.amount
    )

    country_result = check_international_transaction(
        transaction.country
    )

    recent_count = count_recent_transactions(
        transaction.account_id
    )

    velocity_result = check_transaction_velocity(
        recent_count
    )

    risk_priority = {
        "LOW": 1,
        "MEDIUM": 2,
        "HIGH": 3
    }

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

    # Calculate fraud risk score (0-100).
    risk_score = calculate_risk_score(
        amount_flag=amount_result["risk_level"] == "HIGH",
        international_flag=country_result["risk_level"] == "MEDIUM",
        velocity_flag=velocity_result["risk_level"] == "HIGH"
    )

    # Save the transaction first.
    try:
        save_transaction(
            transaction_id=transaction.transaction_id,
            account_id=transaction.account_id,
            amount=transaction.amount,
            merchant=transaction.merchant,
            location=transaction.location,
            country=transaction.country,
            transaction_time=datetime.now(
                timezone.utc
            ).isoformat()
        )

    except sqlite3.IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail="Transaction ID already exists"
        ) from exc

    # Generate and save alerts for risk scores >= 50.
    fraud_alert = None

    if risk_score >= 50:
        fraud_alert = create_fraud_alert(
            transaction_id=transaction.transaction_id,
            account_id=transaction.account_id,
            risk_level=risk_level,
            risk_score=risk_score,
            reason=reason
        )

        save_fraud_alert(fraud_alert)

    return {
        "transaction_id": transaction.transaction_id,
        "account_id": transaction.account_id,
        "amount": transaction.amount,
        "merchant": transaction.merchant,
        "location": transaction.location,
        "risk_level": risk_level,
        "risk_score": risk_score,
        "reason": reason,
        "fraud_alert": fraud_alert
    }


@app.get("/transactions/{account_id}")
def get_account_transactions(
    account_id: str,
    start_date: date | None = None,
    end_date: date | None = None
):

    if (
        start_date is not None
        and end_date is not None
        and start_date > end_date
    ):
        raise HTTPException(
            status_code=400,
            detail="start_date cannot be later than end_date"
        )

    transactions = get_transactions_by_account(
        account_id,
        start_date=(
            start_date.isoformat()
            if start_date
            else None
        ),
        end_date=(
            end_date.isoformat()
            if end_date
            else None
        )
    )

    return {
        "account_id": account_id,
        "total_transactions": len(transactions),
        "transactions": transactions
    }


# Retrieve stored fraud alerts for the dashboard.
@app.get("/fraud-alerts")
def get_all_fraud_alerts():

    alerts = get_fraud_alerts()

    return {
        "total_alerts": len(alerts),
        "alerts": alerts
    }


# Retrieve dashboard summary metrics from SQLite.
@app.get("/dashboard/summary")
def dashboard_summary():

    return get_dashboard_summary()


# Request model for updating a fraud alert.
class FraudAlertStatusUpdate(BaseModel):
    status: str


# Update the investigation status of a fraud alert.
@app.patch("/fraud-alerts/{transaction_id}/status")
def change_fraud_alert_status(
    transaction_id: str,
    request: FraudAlertStatusUpdate
):
    try:
        updated_alert = update_fraud_alert_status(
            transaction_id=transaction_id,
            new_status=request.status
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        ) from exc

    if updated_alert is None:
        raise HTTPException(
            status_code=404,
            detail="Fraud alert not found"
        )

    return {
        "message": "Fraud alert status updated successfully",
        "alert": updated_alert
    }


# Run LangGraph fraud investigation for a saved alert.
@app.get("/fraud-alerts/{transaction_id}/investigate")
def investigate_fraud_alert(transaction_id: str):

    # Reuse the existing database function.
    alerts = get_fraud_alerts()

    # Find the requested fraud alert.
    matching_alert = next(
        (
            alert
            for alert in alerts
            if alert["transaction_id"] == transaction_id
        ),
        None
    )

    if matching_alert is None:
        raise HTTPException(
            status_code=404,
            detail="Fraud alert not found"
        )

    # Prepare the LangGraph workflow input.
    investigation_input = {
        "transaction_id": matching_alert["transaction_id"],
        "account_id": matching_alert["account_id"],
        "risk_level": matching_alert["risk_level"],
        "risk_score": matching_alert["risk_score"],
        "reason": matching_alert["reason"],
        "fraud_indicators": [],
        "recommendation": "",
        "investigation_summary": ""
    }

    # Execute the LangGraph workflow.
    investigation_result = fraud_investigation_agent.invoke(
        investigation_input
    )

    return {
        "transaction_id": investigation_result["transaction_id"],
        "account_id": investigation_result["account_id"],
        "risk_level": investigation_result["risk_level"],
        "risk_score": investigation_result["risk_score"],
        "fraud_indicators": investigation_result["fraud_indicators"],
        "recommendation": investigation_result["recommendation"],
        "investigation_summary": investigation_result[
            "investigation_summary"
        ],
        "alert_status": matching_alert["status"],
        "investigation_type": "RULE_BASED_LANGGRAPH"
    }
