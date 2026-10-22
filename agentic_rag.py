"""
Agentic Customer Support Agent (Upgraded Multi-Company Architecture).
Preserves existing LangGraph state machine, nodes, planning, and tool loop.
Eliminates all local dummy orders (ORDERS_DB) and hardcoded policies (POLICIES).
Grounded strictly in verified uploaded company documents and live integrations.
"""

import os
from typing import Any, Optional, Dict
from dotenv import load_dotenv

from core.knowledge_base import knowledge_base, MultiTenantKnowledgeBase
from core.integrations import (
    get_order_details,
    check_inventory,
    check_return_eligibility,
    integration_manager
)
from core.cache import semantic_cache, MultiTenantSemanticCache
from core.metrics import platform_metrics, PlatformMetrics
from core.guardrails import safety_guardrails, SafetyGuardrails
from core.agent import (
    AgentState,
    Plan,
    plan_step,
    run_tool,
    respond,
    route_after_planning,
    build_customer_support_graph,
    run_production_agent,
    agent_workflow,
    to_text,
    get_llm
)

load_dotenv()


def build_agent():
    """Returns the compiled LangGraph agent workflow."""
    return build_customer_support_graph()


def ask_agent(query: str, company_id: str = "default_company", customer_id: Optional[str] = None) -> str:
    """
    Direct invocation of the agent with real grounded knowledge and integrations.
    Returns the final synthesized response.
    """
    result = run_production_agent(
        company_id=company_id,
        query=query,
        customer_id=customer_id
    )
    return result["response"]


if __name__ == "__main__":
    import sys
    query = sys.argv[1] if len(sys.argv) > 1 else "What is your return policy?"
    print(f"Query: {query}")
    answer = ask_agent(query)
    print(f"Answer: {answer}")
