import os
from src.agent import ResumeScreeningAgent

def test_agent():
    print("Initializing Agent...")
    agent = ResumeScreeningAgent()
    
    # Test 1: Set criteria and screen
    print("\nTest 1: Screening with new criteria...")
    result = agent.screen_candidates(
        role="Backend Engineer",
        seniority="Senior",
        tech_stack="Python, Django, AWS"
    )
    
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print(f"Found {len(result.get('longlist', []))} candidates in longlist.")
        print(f"Found {len(result.get('shortlist', []))} candidates in shortlist.")
        if result.get('shortlist'):
            print("Top candidate:", result['shortlist'][0].get('name'))
            
    # Test 2: Check memory persistence
    print("\nTest 2: Checking memory persistence...")
    agent2 = ResumeScreeningAgent()
    criteria = agent2.get_stored_criteria()
    print(f"Stored criteria: {criteria}")
    
    if criteria and criteria['role'] == "Backend Engineer":
        print("PASS: Memory persisted correctly.")
    else:
        print("FAIL: Memory not persisted.")
        
    # Test 3: Screen using memory (no args)
    print("\nTest 3: Screening using memory...")
    result_mem = agent2.screen_candidates()
    if "error" in result_mem:
        print(f"Error: {result_mem['error']}")
    else:
        print("PASS: Successfully screened using memory.")

if __name__ == "__main__":
    test_agent()
