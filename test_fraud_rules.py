from decimal import Decimal
from fraud_rules import check_transaction_amount


def test_amount_above_threshold():
    result = check_transaction_amount(Decimal("10000.01"))
    assert result["risk_level"] == "HIGH"


def test_amount_at_threshold():
    result = check_transaction_amount(Decimal("10000.00"))
    assert result["risk_level"] == "LOW"


def test_amount_below_threshold():
    result = check_transaction_amount(Decimal("500.00"))
    assert result["risk_level"] == "LOW"


def test_high_transaction_velocity():
    from fraud_rules import check_transaction_velocity

    result = check_transaction_velocity(6)

    assert result["risk_level"] == "HIGH"