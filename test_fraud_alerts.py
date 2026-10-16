
from fraud_alerts import calculate_risk_score


def test_risk_score_no_flags():
    assert calculate_risk_score(False, False, False) == 0


def test_risk_score_high_amount():
    assert calculate_risk_score(True, False, False) == 50


def test_risk_score_international():
    assert calculate_risk_score(False, True, False) == 25


def test_risk_score_velocity():
    assert calculate_risk_score(False, False, True) == 40


def test_risk_score_combined():
    assert calculate_risk_score(True, True, False) == 75


def test_risk_score_capped_at_100():
    assert calculate_risk_score(True, True, True) == 100
