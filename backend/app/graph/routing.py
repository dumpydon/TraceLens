from typing import Literal

from app.graph.state import InvestigationState


def route_after_verification(state: InvestigationState) -> Literal["refine_investigation", "generate_report"]:
    verification = state["verification"]
    if verification and verification.is_sufficient:
        return "generate_report"
    if state["iteration_count"] >= state["max_iterations"]:
        return "generate_report"
    return "refine_investigation"

