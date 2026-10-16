
from datetime import datetime, timezone


def create_fraud_alert(
    transaction_id: str,
    account_id: str,
    risk_level: str,
    risk_score: int,
    reason: str
) -> dict:
    return {
        "transaction_id": transaction_id,
        "account_id": account_id,
        "risk_level": risk_level,
        "risk_score": risk_score,
        "reason": reason,
        "status": "OPEN",
        "created_at": datetime.now(timezone.utc).isoformat()
    }


def calculate_risk_score(
    amount_flag: bool,
    international_flag: bool,
    velocity_flag: bool
) -> int:
    score = 0

    if amount_flag:
        score += 50

    if international_flag:
        score += 25

    if velocity_flag:
        score += 40

    return min(score, 100)
