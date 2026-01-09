#!/usr/bin/env python3
"""
Test the add_faq MCP tool via HTTP endpoint
"""

import requests
import json

# MCP Server endpoint
MCP_URL = "http://localhost:9010/mcp"

def call_mcp_tool(tool_name, arguments):
    """Call an MCP tool via HTTP"""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"
    }
    response = requests.post(MCP_URL, json=payload, headers=headers)
    return response.json()

def test_add_faq():
    """Test the add_faq tool"""
    
    print("=" * 60)
    print("Testing FAQ Data Ingestion Tool via HTTP")
    print("=" * 60)
    
    # Test 1: Add a valid FAQ
    print("\n1. Testing: Add a valid FAQ")
    result = call_mcp_tool("add_faq", {
        "question": "What is the refund policy for the bootcamp?",
        "answer": "The bootcamp is free of charge, so there is no refund policy. However, if you have paid for any additional services, please contact support at internship-support@vicharanashala.zohodesk.in.",
        "category": "Program Overview"
    })
    print(f"Response: {json.dumps(result, indent=2)}")
    
    # Test 2: Try to add exact duplicate
    print("\n2. Testing: Add exact duplicate (should fail)")
    result = call_mcp_tool("add_faq", {
        "question": "What is the refund policy for the bootcamp?",
        "answer": "Different answer",
        "category": "Program Overview"
    })
    print(f"Response: {json.dumps(result, indent=2)}")
    
    # Test 3: Try to add similar question (fuzzy match)
    print("\n3. Testing: Add similar question - fuzzy match (should fail)")
    result = call_mcp_tool("add_faq", {
        "question": "What is the refund policy for this bootcamp?",
        "answer": "This is a different answer but similar question",
        "category": "Program Overview"
    })
    print(f"Response: {json.dumps(result, indent=2)}")
    
    # Test 4: Invalid input - question too short
    print("\n4. Testing: Question too short (should fail)")
    result = call_mcp_tool("add_faq", {
        "question": "Short?",
        "answer": "This is a valid answer that is long enough to pass validation",
        "category": "Test"
    })
    print(f"Response: {json.dumps(result, indent=2)}")
    
    # Test 5: Invalid input - answer too short
    print("\n5. Testing: Answer too short (should fail)")
    result = call_mcp_tool("add_faq", {
        "question": "This is a valid question that is long enough?",
        "answer": "Short",
        "category": "Test"
    })
    print(f"Response: {json.dumps(result, indent=2)}")
    
    # Test 6: Search for newly added FAQ
    print("\n6. Testing: Search for newly added FAQ")
    result = call_mcp_tool("search_faq", {
        "query": "refund policy",
        "top_k": 3
    })
    print(f"Response: {json.dumps(result, indent=2)}")
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)

if __name__ == "__main__":
    test_add_faq()
