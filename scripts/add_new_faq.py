#!/usr/bin/env python3
"""
Add a new FAQ to MongoDB using the add_faq tool
This demonstrates the actual usage of the add_faq MCP tool
"""

import asyncio
import sys
sys.path.insert(0, '/app')

from pymongo import MongoClient
import os
from datetime import datetime
from difflib import SequenceMatcher
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# Import from faq.py
from faq import get_embedding_function, invalidate_caches

async def add_new_faq():
    """Add a new FAQ using the add_faq tool logic"""
    
    print("=" * 70)
    print("Adding New FAQ to MongoDB")
    print("=" * 70)
    
    # New FAQ to add
    new_faq = {
        "question": "Can I get a recommendation letter after completing the bootcamp?",
        "answer": "Recommendation letters are not guaranteed. You may request one from the course instructor after successfully completing the internship, and it will be at their discretion based on your performance during the bootcamp.",
        "category": "Stipend & Recommendation Letters"
    }
    
    print(f"\n📝 New FAQ Details:")
    print(f"   Question: {new_faq['question']}")
    print(f"   Answer: {new_faq['answer'][:80]}...")
    print(f"   Category: {new_faq['category']}")
    
    # Get environment variables
    MONGODB_URI = os.getenv('MONGODB_URI')
    DB_NAME = os.getenv('DB_NAME', 'faq_bootcamp')
    COLLECTION_NAME = os.getenv('COLLECTION_NAME', 'questions')
    
    # Connect to MongoDB
    print(f"\n[1] Connecting to MongoDB...")
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]
    
    initial_count = collection.count_documents({})
    print(f"    ✓ Current FAQ count: {initial_count}")
    
    # Validation
    print(f"\n[2] Validating Input...")
    if len(new_faq['question'].strip()) < 10:
        print(f"    ✗ Question too short (minimum 10 characters)")
        return
    if len(new_faq['answer'].strip()) < 20:
        print(f"    ✗ Answer too short (minimum 20 characters)")
        return
    print(f"    ✓ Input validation passed")
    
    # Check for exact duplicate
    print(f"\n[3] Checking for Exact Duplicate...")
    existing = collection.find_one({"question": new_faq['question'].strip()})
    if existing:
        print(f"    ✗ Exact duplicate found (ID: {existing.get('question_id')})")
        client.close()
        return
    print(f"    ✓ No exact duplicate")
    
    # Fuzzy matching check
    print(f"\n[4] Checking Fuzzy Matching (85% threshold)...")
    FUZZY_THRESHOLD = 0.85
    all_faqs = list(collection.find({}, {'question': 1, 'question_id': 1}))
    
    for faq in all_faqs:
        existing_question = faq.get('question', '')
        similarity = SequenceMatcher(None, new_faq['question'].strip().lower(), existing_question.lower()).ratio()
        if similarity > FUZZY_THRESHOLD:
            print(f"    ✗ Similar question found (ID: {faq.get('question_id')}, {similarity*100:.1f}% similar)")
            print(f"    Question: '{existing_question}'")
            client.close()
            return
    print(f"    ✓ No fuzzy match duplicates")
    
    # Semantic similarity check (skip if no embeddings)
    print(f"\n[5] Checking Semantic Similarity (90% threshold)...")
    print(f"    ℹ Skipping (requires embedding generation)")
    
    # Generate question ID
    print(f"\n[6] Generating Question ID...")
    all_faqs_full = list(collection.find({}))
    category_questions = [
        faq for faq in all_faqs_full 
        if faq.get('category', '').lower() == new_faq['category'].lower()
    ]
    
    max_num = 0
    for faq in category_questions:
        qid = faq.get('question_id', '')
        if '.' in qid:
            try:
                parts = qid.split('.')
                num = int(parts[1])
                max_num = max(max_num, num)
            except (ValueError, IndexError):
                continue
    
    if category_questions:
        first_qid = category_questions[0].get('question_id', 'Q11.1')
        category_num = first_qid.split('.')[0].replace('Q', '')
    else:
        # New category - assign next category number
        all_category_nums = set()
        for faq in all_faqs_full:
            qid = faq.get('question_id', '')
            if '.' in qid:
                try:
                    cat_num = int(qid.split('.')[0].replace('Q', ''))
                    all_category_nums.add(cat_num)
                except:
                    pass
        category_num = str(max(all_category_nums) + 1) if all_category_nums else '1'
    
    question_id = f"Q{category_num}.{max_num + 1}"
    print(f"    ✓ Generated Question ID: {question_id}")
    
    # Create FAQ document
    print(f"\n[7] Creating FAQ Document...")
    faq_doc = {
        "question_id": question_id,
        "question": new_faq['question'].strip(),
        "answer": new_faq['answer'].strip(),
        "category": new_faq['category'].strip(),
        "created_at": datetime.utcnow().isoformat(),
    }
    print(f"    ✓ Document created")
    
    # Insert into MongoDB
    print(f"\n[8] Inserting into MongoDB...")
    result = collection.insert_one(faq_doc.copy())
    print(f"    ✓ FAQ inserted successfully!")
    print(f"    ✓ MongoDB ID: {result.inserted_id}")
    
    # Verify insertion
    print(f"\n[9] Verifying Insertion...")
    inserted_faq = collection.find_one({"question_id": question_id})
    if inserted_faq:
        print(f"    ✓ FAQ verified in database")
        print(f"    ✓ Question ID: {inserted_faq['question_id']}")
        print(f"    ✓ Category: {inserted_faq['category']}")
        print(f"    ✓ Created: {inserted_faq['created_at']}")
    
    final_count = collection.count_documents({})
    print(f"\n[10] Final Status:")
    print(f"    ✓ Previous count: {initial_count}")
    print(f"    ✓ New count: {final_count}")
    print(f"    ✓ Successfully added 1 FAQ")
    
    client.close()
    
    # Invalidate caches
    print(f"\n[11] Invalidating Caches...")
    invalidate_caches()
    print(f"    ✓ Caches cleared - new FAQ will be searchable")
    
    print("\n" + "=" * 70)
    print("✅ NEW FAQ ADDED SUCCESSFULLY!")
    print("=" * 70)
    print(f"\n📋 Summary:")
    print(f"   Question ID: {question_id}")
    print(f"   Question: {new_faq['question']}")
    print(f"   Category: {new_faq['category']}")
    print(f"   Total FAQs: {final_count}")

if __name__ == "__main__":
    asyncio.run(add_new_faq())
