
import sqlite3
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_transaction_saving():
    """Prevent API tests from writing to the real SQLite database."""
    with (
        patch("main.save_transaction"),
        patch("main.save_fraud_alert")
    ):
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


def test_get_account_transactions_with_date_filters():
    mock_transactions = [
        {
            "transaction_id": "TXN-1001",
            "account_id": "ACC-1001",
            "amount": "750",
            "merchant": "Grocery Store",
            "location": "Minnesota",
            "country": "US",
            "transaction_time": "2026-10-15T10:00:00+00:00"
        }
    ]

    with patch(
        "main.get_transactions_by_account",
        return_value=mock_transactions
    ) as mock_get_transactions:
        response = client.get(
            "/transactions/ACC-1001"
            "?start_date=2026-10-12&end_date=2026-10-18"
        )

    assert response.status_code == 200
    assert response.json()["total_transactions"] == 1

    mock_get_transactions.assert_called_once_with(
        "ACC-1001",
        start_date="2026-10-12",
        end_date="2026-10-18"
    )


def test_get_account_transactions_invalid_date_range():
    response = client.get(
        "/transactions/ACC-1001"
        "?start_date=2026-10-20&end_date=2026-10-10"
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "start_date cannot be later than end_date"
    )


def test_analyze_transaction_returns_risk_score():
    transaction = {
        "transaction_id": "TXN-RISK-001",
        "account_id": "ACC-RISK-001",
        "amount": "15000.00",
        "merchant": "Test Merchant",
        "location": "London",
        "country": "UK"
    }

    with patch("main.count_recent_transactions", return_value=0):
        response = client.post(
            "/transactions/analyze",
            json=transaction
        )

    assert response.status_code == 200

    data = response.json()

    assert data["risk_level"] == "HIGH"
    assert data["risk_score"] == 75


def test_high_risk_transaction_generates_alert():
    transaction = {
        "transaction_id": "TXN-ALERT-001",
        "account_id": "ACC-ALERT-001",
        "amount": "15000.00",
        "merchant": "Test Merchant",
        "location": "London",
        "country": "UK"
    }

    with patch("main.count_recent_transactions", return_value=0):
        response = client.post(
            "/transactions/analyze",
            json=transaction
        )

    assert response.status_code == 200

    data = response.json()

    assert data["risk_score"] == 75
    assert data["fraud_alert"] is not None
    assert data["fraud_alert"]["status"] == "OPEN"
    assert data["fraud_alert"]["transaction_id"] == "TXN-ALERT-001"


def test_low_risk_transaction_does_not_generate_alert():
    transaction = {
        "transaction_id": "TXN-ALERT-002",
        "account_id": "ACC-ALERT-002",
        "amount": "100.00",
        "merchant": "Grocery Store",
        "location": "Minnesota",
        "country": "US"
    }

    with patch("main.count_recent_transactions", return_value=0):
        response = client.post(
            "/transactions/analyze",
            json=transaction
        )

    assert response.status_code == 200

    data = response.json()

    assert data["risk_score"] == 0
    assert data["fraud_alert"] is None


def test_high_risk_alert_is_saved():
    transaction = {
        "transaction_id": "TXN-SAVE-ALERT-001",
        "account_id": "ACC-SAVE-ALERT-001",
        "amount": "15000.00",
        "merchant": "Test Merchant",
        "location": "London",
        "country": "UK"
    }

    with (
        patch("main.count_recent_transactions", return_value=0),
        patch("main.save_fraud_alert") as mock_save_alert
    ):
        response = client.post(
            "/transactions/analyze",
            json=transaction
        )

    assert response.status_code == 200
    assert response.json()["risk_score"] == 75

    mock_save_alert.assert_called_once()

    saved_alert = mock_save_alert.call_args.args[0]

    assert saved_alert["transaction_id"] == "TXN-SAVE-ALERT-001"
    assert saved_alert["risk_score"] == 75
    assert saved_alert["status"] == "OPEN"


def test_low_risk_alert_is_not_saved():
    transaction = {
        "transaction_id": "TXN-NO-ALERT-001",
        "account_id": "ACC-NO-ALERT-001",
        "amount": "100.00",
        "merchant": "Grocery Store",
        "location": "Minnesota",
        "country": "US"
    }

    with (
        patch("main.count_recent_transactions", return_value=0),
        patch("main.save_fraud_alert") as mock_save_alert
    ):
        response = client.post(
            "/transactions/analyze",
            json=transaction
        )

    assert response.status_code == 200
    assert response.json()["risk_score"] == 0

    mock_save_alert.assert_not_called()


def test_get_all_fraud_alerts():
    mock_alerts = [
        {
            "transaction_id": "TXN-ALERT-001",
            "account_id": "ACC-ALERT-001",
            "risk_level": "HIGH",
            "risk_score": 75,
            "reason": "High transaction amount detected",
            "status": "OPEN",
            "created_at": "2026-10-16T20:42:48+00:00"
        }
    ]

    with patch(
        "main.get_fraud_alerts",
        return_value=mock_alerts
    ) as mock_get_alerts:
        response = client.get("/fraud-alerts")

    assert response.status_code == 200

    data = response.json()

    assert data["total_alerts"] == 1
    assert len(data["alerts"]) == 1
    assert data["alerts"][0]["transaction_id"] == "TXN-ALERT-001"
    assert data["alerts"][0]["risk_score"] == 75
    assert data["alerts"][0]["status"] == "OPEN"

    mock_get_alerts.assert_called_once_with()


def test_dashboard_summary():
    from unittest.mock import patch
    from fastapi.testclient import TestClient
    from main import app

    expected_summary = {
        "total_alerts": 1,
        "open_alerts": 1,
        "high_risk_alerts": 1,
        "average_risk_score": 75
    }

    with patch(
        "main.get_dashboard_summary",
        return_value=expected_summary
    ):
        client = TestClient(app)
        response = client.get("/dashboard/summary")

    assert response.status_code == 200
    assert response.json() == expected_summary
