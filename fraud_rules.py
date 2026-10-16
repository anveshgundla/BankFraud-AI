
from decimal import Decimal

HIGH_AMOUNT_THRESHOLD = Decimal("10000.00")


def check_transaction_amount(amount: Decimal) -> dict:
    if amount > HIGH_AMOUNT_THRESHOLD:
        return {
            "risk_level": "HIGH",
            "reason": "Transaction exceeds the configured amount threshold"
        }

    return {
        "risk_level": "LOW",
        "reason": "Transaction is within the configured amount threshold"
    }
