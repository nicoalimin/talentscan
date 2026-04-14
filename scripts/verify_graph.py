import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from langchain_core.messages import HumanMessage
from src.graph import agent_graph


def verify_graph():
    if agent_graph is None:
        print("ERROR: agent_graph is None — check ANTHROPIC_API_KEY")
        return

    print("Testing 'process' action...")
    result = agent_graph.invoke({"messages": [HumanMessage(content="process resumes")]})
    last = result["messages"][-1]
    print("Result:", last.content if hasattr(last, "content") else last)

    print("\nTesting 'query all candidates'...")
    result = agent_graph.invoke({"messages": [HumanMessage(content="show me all candidates")]})
    last = result["messages"][-1]
    print("Result:", last.content if hasattr(last, "content") else last)


if __name__ == "__main__":
    verify_graph()
