
from typing import TypedDict

from langgraph.graph import StateGraph, START, END


class FraudInvestigationState(TypedDict):
    transaction_id: str
    account_id: str
    risk_level: str
    risk_score: int
    reason: str
    fraud_indicators: list[str]
    recommendation: str
    investigation_summary: str


def analyze_fraud_indicators(
    state: FraudInvestigationState
) -> dict:
    reason = state["reason"].lower()

    # Split individual fraud rule results.
    # This prevents keywords from different rules
    # from causing false positive detections.
    rule_results = [
        item.strip()
        for item in reason.split(";")
    ]

    indicators = []

    for rule in rule_results:

        # Rule 1: High transaction amount
        if (
            "amount" in rule
            and "exceeds" in rule
        ):
            indicators.append(
                "Transaction exceeds the configured amount threshold"
            )

        # Rule 2: International transaction
        elif "international transaction detected" in rule:
            indicators.append(
                "International transaction detected"
            )

        # Rule 3: High transaction velocity
        elif (
            "frequency" in rule
            and (
                "exceeds" in rule
                or "high" in rule
                or "unusual" in rule
            )
            and "within" not in rule
        ):
            indicators.append(
                "Potential high transaction velocity"
            )

    if not indicators:
        indicators.append(
            "No specific fraud indicators identified"
        )

    return {
        "fraud_indicators": indicators
    }


def generate_recommendation(
    state: FraudInvestigationState
) -> dict:
    risk_score = state["risk_score"]

    if risk_score >= 70:
        recommendation = (
            "Prioritize manual investigation. "
            "Verify the transaction with the account holder "
            "through an approved banking channel."
        )

    elif risk_score >= 50:
        recommendation = (
            "Review the transaction and account activity "
            "before determining the next action."
        )

    else:
        recommendation = (
            "Continue routine monitoring."
        )

    return {
        "recommendation": recommendation
    }


def generate_investigation_summary(
    state: FraudInvestigationState
) -> dict:
    indicators = "; ".join(
        state["fraud_indicators"]
    )

    summary = (
        f"Transaction {state['transaction_id']} "
        f"for account {state['account_id']} "
        f"has a risk score of {state['risk_score']}/100. "
        f"Identified indicators: {indicators}. "
        f"Recommendation: {state['recommendation']}"
    )

    return {
        "investigation_summary": summary
    }


# Initialize LangGraph workflow
workflow = StateGraph(FraudInvestigationState)

# Register investigation nodes
workflow.add_node(
    "analyze_indicators",
    analyze_fraud_indicators
)

workflow.add_node(
    "generate_recommendation",
    generate_recommendation
)

workflow.add_node(
    "generate_summary",
    generate_investigation_summary
)

# Define workflow execution sequence
workflow.add_edge(
    START,
    "analyze_indicators"
)

workflow.add_edge(
    "analyze_indicators",
    "generate_recommendation"
)

workflow.add_edge(
    "generate_recommendation",
    "generate_summary"
)

workflow.add_edge(
    "generate_summary",
    END
)

# Compile the fraud investigation agent
fraud_investigation_agent = workflow.compile()
