from typing import TypedDict, List, Dict, Optional
from langgraph.graph import StateGraph, END
from src.agent import ResumeScreeningAgent
from src.processor import process_resumes
import os


class AgentState(TypedDict):
    messages: List[str]
    role: str
    seniority: str
    tech_stack: str
    results: Optional[Dict]
    next_action: Optional[str]

def process_resumes_node(state: AgentState):
    resumes_dir = "resumes"
    if not os.path.exists(resumes_dir):
        return {"messages": [f"Directory `{resumes_dir}` not found."]}
    
    process_resumes(resumes_dir)
    return {"messages": [f"Processing complete! Checked `{resumes_dir}`."]}

def screen_candidates_node(state: AgentState):
    role = state.get("role", "Backend Engineer")
    seniority = state.get("seniority", "Senior")
    tech_stack = state.get("tech_stack", "Python, Django, AWS")
    
    agent = ResumeScreeningAgent()
    results = agent.screen_candidates(role, seniority, tech_stack)
    
    return {"results": results, "messages": ["Screening complete."]}

def router_node(state: AgentState):
    # Simple router based on next_action set by the UI or previous steps
    # In a real agent, an LLM would decide this based on messages.
    # Here we rely on the input state to direct the graph.
    action = state.get("next_action")
    if action == "process":
        return "process_resumes"
    elif action == "screen":
        return "screen_candidates"
    return END

# Define the graph
workflow = StateGraph(AgentState)

workflow.add_node("process_resumes", process_resumes_node)
workflow.add_node("screen_candidates", screen_candidates_node)

workflow.set_conditional_entry_point(
    router_node,
    {
        "process_resumes": "process_resumes",
        "screen_candidates": "screen_candidates",
        END: END
    }
)

workflow.add_edge("process_resumes", END)
workflow.add_edge("screen_candidates", END)

app_graph = workflow.compile()
