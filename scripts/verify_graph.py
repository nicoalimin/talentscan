import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.graph import app_graph


def verify_graph():
    
    print("Testing 'process' action...")
    inputs = {
        "role": "Backend Engineer",
        "seniority": "Senior",
        "tech_stack": "Python",
        "next_action": "process",
        "messages": ["process"]
    }
    result = app_graph.invoke(inputs)
    print("Result:", result.get("messages"))
    
    print("\nTesting 'screen' action...")
    inputs["next_action"] = "screen"
    inputs["messages"] = ["screen"]
    result = app_graph.invoke(inputs)
    results = result.get("results", {})
    print("Candidates count:", len(results.get("candidates", [])))

if __name__ == "__main__":
    verify_graph()
