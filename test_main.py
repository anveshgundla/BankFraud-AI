
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_high_risk_transaction():
    transaction = {
        "transaction_id": "TXN1005",
        "account_id": "ACC1001",
        "amount": 25000,
        "merchant": "Electronics Store",
        "location": "New York"
    }

    response = client.post(
        "/transactions/analyze",
        json=transaction
    )

    assert response.status_code == 200
    assert response.json()["risk_level"] == "HIGH"

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

def test_invalid_transaction_amount():
    transaction = {
        "transaction_id": "TXN1007",
        "account_id": "ACC1001",
        "amount": -500,
        "merchant": "Grocery Store",
        "location": "Minnesota"
    }

    response = client.post(
        "/transactions/analyze",
        json=transaction
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == [
        "body", "amount"
    ]
