
from fastapi import FastAPI
from fraud_rules import check_transaction_amount

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


from pydantic import BaseModel, Field
from decimal import Decimal

class Transaction(BaseModel):
    transaction_id: str
    account_id: str
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    merchant: str
    location: str



@app.post("/transactions/analyze")
@app.post("/transactions/analyze")
def analyze_transaction(transaction: Transaction):
    result = check_transaction_amount(transaction.amount)
    risk_level = result["risk_level"]
    reason = result["reason"]

    return {
        "transaction_id": transaction.transaction_id,
        "account_id": transaction.account_id,
        "amount": transaction.amount,
        "merchant": transaction.merchant,
        "location": transaction.location,
        "risk_level": risk_level,
        "reason": reason
    }

def test_low_risk_transaction():
    transaction = {
        "transaction_id": "TXN1006",
        "account_id": "ACC1001",
        "amount": 500,
        "merchant": "Grocery Store",
        "location": "Minnesota"
    }

    response = client.post(
        "/transactions/analyze",
        json=transaction
    )

    assert response.status_code == 200
    assert response.json()["risk_level"] == "LOW"
