
import sqlite3
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_transaction_saving():
    """Prevent API tests from writing to the real SQLite database."""
    with patch("main.save_transaction"):
        yield


def test_high_risk_transaction():
    transaction = {
        "transaction_id": "TXN1005",
        "account_id": "ACC1001",
        "amount": 25000,
        "merchant": "Electronics Store",
        "location": "New York"
    }

    with patch("main.count_recent_transactions", return_value=0):
        response = client.post("/transactions/analyze", json=transaction)

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

    with patch("main.count_recent_transactions", return_value=0):
        response = client.post("/transactions/analyze", json=transaction)

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

    response = client.post("/transactions/analyze", json=transaction)

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "amount"]


def test_international_transaction():
    transaction = {
        "transaction_id": "TXN1008",
        "account_id": "ACC1001",
        "amount": 500,
        "merchant": "Online Store",
        "location": "Hyderabad",
        "country": "IN"
    }

    with patch("main.count_recent_transactions", return_value=0):
        response = client.post("/transactions/analyze", json=transaction)

    assert response.status_code == 200
    assert response.json()["risk_level"] == "MEDIUM"


def test_high_value_international_transaction():
    transaction = {
        "transaction_id": "TXN1009",
        "account_id": "ACC1001",
        "amount": 25000,
        "merchant": "Electronics Store",
        "location": "Hyderabad",
        "country": "IN"
    }

    with patch("main.count_recent_transactions", return_value=0):
        response = client.post("/transactions/analyze", json=transaction)

    assert response.status_code == 200
    assert response.json()["risk_level"] == "HIGH"


def test_high_velocity_transaction():
    transaction = {
        "transaction_id": "TXN-006",
        "account_id": "ACC-1001",
        "amount": 500,
        "merchant": "Grocery Store",
        "location": "Minnesota",
        "country": "US"
    }

    with patch("main.count_recent_transactions", return_value=6):
        response = client.post("/transactions/analyze", json=transaction)

    assert response.status_code == 200
    assert response.json()["risk_level"] == "HIGH"
    assert "High transaction frequency detected" in response.json()["reason"]


def test_duplicate_transaction_id():
    transaction = {
        "transaction_id": "TXN-DUPLICATE-001",
        "account_id": "ACC-TEST-2001",
        "amount": 750,
        "merchant": "Grocery Store",
        "location": "Minnesota",
        "country": "US"
    }

    with patch("main.count_recent_transactions", return_value=0):
        with patch(
            "main.save_transaction",
            side_effect=sqlite3.IntegrityError(
                "UNIQUE constraint failed: transactions.transaction_id"
            )
        ):
            response = client.post(
                "/transactions/analyze",
                json=transaction
            )

    assert response.status_code == 409
    assert response.json()["detail"] == "Transaction ID already exists"
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