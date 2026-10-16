
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
def check_international_transaction(country: str) -> dict:
    if country.strip().upper() != "US":
        return {
            "risk_level": "MEDIUM",
            "reason": "International transaction detected"
        }

    return {
        "risk_level": "LOW",
        "reason": "Domestic transaction"
    }
def check_transaction_velocity(transactions_last_10_minutes: int) -> dict:
    if transactions_last_10_minutes >= 5:
        return {
            "risk_level": "HIGH",
            "reason": "High transaction frequency detected within 10 minutes"
        }

    return {
        "risk_level": "LOW",
        "reason": "Transaction frequency is within the configured limit"
    }
