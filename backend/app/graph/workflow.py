from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.graph.nodes import InvestigationNodes
from app.graph.routing import route_after_verification
from app.graph.state import InvestigationState


def build_workflow(nodes: InvestigationNodes | None = None, checkpointer=None):
    nodes = nodes or InvestigationNodes()
    builder = StateGraph(InvestigationState)
    builder.add_node("load_incident", nodes.load_incident)
    builder.add_node("collect_runtime_context", nodes.collect_runtime_context)
    builder.add_node("analyze_runtime_evidence", nodes.analyze_runtime_evidence)
    builder.add_node("retrieve_operational_knowledge", nodes.retrieve_operational_knowledge)
    builder.add_node("generate_hypothesis", nodes.generate_hypothesis)
    builder.add_node("verify_hypothesis", nodes.verify_hypothesis)
    builder.add_node("refine_investigation", nodes.refine_investigation)
    builder.add_node("generate_report", nodes.generate_report)
    builder.add_edge(START, "load_incident")
    builder.add_edge("load_incident", "collect_runtime_context")
    builder.add_edge("collect_runtime_context", "analyze_runtime_evidence")
    builder.add_edge("analyze_runtime_evidence", "retrieve_operational_knowledge")
    builder.add_edge("retrieve_operational_knowledge", "generate_hypothesis")
    builder.add_edge("generate_hypothesis", "verify_hypothesis")
    builder.add_conditional_edges("verify_hypothesis", route_after_verification)
    builder.add_edge("refine_investigation", "retrieve_operational_knowledge")
    builder.add_edge("generate_report", END)
    return builder.compile(checkpointer=checkpointer)

