#!/usr/bin/env python3
"""
Test script for the add_faq MCP tool
Run this after starting the FAQ MCP server
"""

import asyncio
from faq import add_faq, search_faqs, initialize

async def test_add_faq():
    """Test adding a new FAQ and searching for it"""
    
    print("=" * 60)
    print("Testing FAQ Data Ingestion Tool")
    print("=" * 60)
    
    # Initialize the system
    print("\n1. Initializing FAQ system...")
    await initialize()
    
    # Test 1: Add a valid FAQ
    print("\n2. Testing: Add a valid FAQ")
    result = await add_faq(
        question="What is the refund policy for the bootcamp?",
        answer="The bootcamp is free of charge, so there is no refund policy. However, if you have paid for any additional services, please contact support.",
        category="Program Overview"
    )
    print(f"   Result: {result.success}")
    print(f"   Message: {result.message}")
    print(f"   Question ID: {result.question_id}")
    
    # Test 2: Try to add duplicate
    print("\n3. Testing: Add duplicate FAQ (should fail)")
    result = await add_faq(
        question="What is the refund policy for the bootcamp?",
        answer="Different answer",
        category="Program Overview"
    )
    print(f"   Result: {result.success}")
    print(f"   Message: {result.message}")
    
    # Test 3: Try to add similar question (fuzzy match)
    print("\n4. Testing: Add similar question - fuzzy match (should fail)")
    result = await add_faq(
        question="What is the refund policy for this bootcamp?",
        answer="This is a different answer but similar question",
        category="Program Overview"
    )
    print(f"   Result: {result.success}")
    print(f"   Message: {result.message}")
    
    # Test 4: Invalid input - question too short
    print("\n5. Testing: Question too short (should fail)")
    result = await add_faq(
        question="Short?",
        answer="This is a valid answer that is long enough to pass validation",
        category="Test"
    )
    print(f"   Result: {result.success}")
    print(f"   Message: {result.message}")
    
    # Test 5: Invalid input - answer too short
    print("\n6. Testing: Answer too short (should fail)")
    result = await add_faq(
        question="This is a valid question that is long enough?",
        answer="Short answer",
        category="Test"
    )
    print(f"   Result: {result.success}")
    print(f"   Message: {result.message}")
    
    # Test 6: Search for newly added FAQ
    print("\n7. Testing: Search for newly added FAQ")
    search_results = await search_faqs("refund policy", top_k=3)
    print(f"   Found {len(search_results)} results")
    if search_results:
        print(f"   Top result: {search_results[0].question}")
        print(f"   Similarity: {search_results[0].metadata.similarity_score:.3f}")
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_add_faq())
