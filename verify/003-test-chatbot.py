#!/usr/bin/env python3
"""
Test the Data Assistant chatbot flow end-to-end
"""
import requests
import time
import sys

BASE_URL = "http://localhost:8000"

def test_chatbot_flow():
    # 1. Get a test run ID (use existing or create new)
    runs_resp = requests.get(f"{BASE_URL}/api/runs")
    runs = runs_resp.json()
    
    if not runs:
        print("❌ No runs found for testing")
        return False
    
    run_id = runs[0]['run_id']
    print(f"✓ Using run: {run_id}")
    
    # 2. Send a modification request (use unambiguous action)
    chat_resp = requests.post(
        f"{BASE_URL}/api/runs/{run_id}/chat",
        json={"message": "Clear column G for all candidates"}
    )
    
    if chat_resp.status_code != 200:
        print(f"❌ Chat request failed: {chat_resp.status_code}")
        return False
    
    response = chat_resp.json()['response']
    print(f"✓ Got chatbot response: {response[:100]}...")
    
    # 3. Verify pending_action was saved
    time.sleep(0.5)  # Allow DB write
    run_resp = requests.get(f"{BASE_URL}/api/runs/{run_id}")
    run_data = run_resp.json()
    
    if not run_data.get('pending_action'):
        print("❌ pending_action was not saved to database")
        print(f"Response included: {response}")
        return False
    
    print("✓ pending_action saved to database")
    
    # 4. Execute the action
    run_resp = requests.post(
        f"{BASE_URL}/api/runs/{run_id}/chat",
        json={"message": "run"}
    )
    
    if run_resp.status_code != 200:
        print(f"❌ Run command failed: {run_resp.status_code}")
        return False
    
    run_response = run_resp.json()['response']
    
    if "no pending action" in run_response.lower():
        print(f"❌ Got 'no pending action' error: {run_response}")
        return False
    
    if "✅" not in run_response and "applied" not in run_response.lower():
        print(f"❌ Unexpected response to 'run': {run_response}")
        return False
    
    print("✓ Action executed successfully")
    
    # 5. Verify pending_action was cleared
    time.sleep(0.5)
    run_resp = requests.get(f"{BASE_URL}/api/runs/{run_id}")
    run_data = run_resp.json()
    
    if run_data.get('pending_action'):
        print("❌ pending_action was not cleared after execution")
        return False
    
    print("✓ pending_action cleared after execution")
    
    return True

if __name__ == "__main__":
    try:
        success = test_chatbot_flow()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Test exception: {e}")
        sys.exit(1)
