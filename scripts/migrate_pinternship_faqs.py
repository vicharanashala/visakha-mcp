#!/usr/bin/env python3
"""
Migrate FAQ data from JSON file to MongoDB
This script:
1. Reads FAQ data from JSON file in FAQ_Data directory
2. Clears existing FAQ data from MongoDB
3. Generates embeddings using BGE-large-en-v1.5
4. Loads data into MongoDB
"""

import os
import json
import asyncio
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from pymongo import MongoClient
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Configuration
MONGODB_URI = os.getenv('MONGODB_URI')
DB_NAME = os.getenv('DB_NAME', "faq_bootcamp")
COLLECTION_NAME = os.getenv('COLLECTION_NAME', "questions")
EMBEDDING_MODEL = 'BAAI/bge-large-en-v1.5'

# Path to FAQ data file
# Path to FAQ data file
# Allow overriding via environment variable
custom_path = os.getenv('FAQ_FILE_PATH')
if custom_path:
    FAQ_DATA_FILE = Path(custom_path)
elif Path('/app/FAQ_Data').exists():
    # Running in Docker container (default fallback)
    FAQ_DATA_FILE = Path('/app/FAQ_Data/latest/pinternship_faqs.json')
else:
    # Running locally (relative to script location)
    FAQ_DATA_FILE = Path(__file__).parent.parent / 'FAQ_Data' / 'latest' / 'pinternship_faqs.json'


def load_faq_data():
    """Load FAQ data from JSON file."""
    if not FAQ_DATA_FILE.exists():
        raise FileNotFoundError(f"FAQ data file not found: {FAQ_DATA_FILE}")
    
    with open(FAQ_DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data['faqs'], data.get('source', 'Unknown'), data.get('total_faqs', len(data['faqs']))


def generate_question_id(category_id: int, question_num: int) -> str:
    """Generate question ID based on category ID."""
    return f"Q{category_id}.{question_num}"


def main():
    print("=" * 80)
    print("FAQ MIGRATION SCRIPT - Pinternship Data")
    print("=" * 80)
    
    # Load FAQ data from file
    print(f"\n[1] Loading FAQ data from file...")
    print(f"    File: {FAQ_DATA_FILE}")
    try:
        faq_data, source, total_count = load_faq_data()
        print(f"    ✓ Loaded {len(faq_data)} FAQs from {source}")
    except Exception as e:
        print(f"    ✗ Error loading FAQ data: {e}")
        return
    
    # Connect to MongoDB
    print(f"\n[2] Connecting to MongoDB...")
    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]
        
        current_count = collection.count_documents({})
        print(f"    ✓ Current FAQ count: {current_count}")
    except Exception as e:
        print(f"    ✗ MongoDB connection failed: {e}")
        return
    
    # Clear existing data
    print(f"\n[3] Clearing existing FAQ data...")
    result = collection.delete_many({})
    print(f"    ✓ Deleted {result.deleted_count} documents")
    
    # Load embedding model
    print(f"\n[4] Loading embedding model: {EMBEDDING_MODEL}")
    try:
        model = SentenceTransformer(EMBEDDING_MODEL)
        print(f"    ✓ Model loaded")
    except Exception as e:
        print(f"    ✗ Error loading model: {e}")
        client.close()
        return
    
    # Process and insert FAQs
    print(f"\n[5] Processing {len(faq_data)} FAQs...")
    
    # Group by category to assign question numbers
    category_counters = {}
    documents = []
    
    for faq in tqdm(faq_data, desc="Generating embeddings"):
        category = faq['category']
        
        # Increment counter for this category
        if category not in category_counters:
            category_counters[category] = 0
        category_counters[category] += 1
        
        # Get category_id from data (default to 99 if missing)
        category_id = faq.get('category_id', 99)
        
        # Generate question ID
        question_id = generate_question_id(category_id, category_counters[category])
        
        # Generate embedding from combined question + answer
        # This provides richer semantic context for better search accuracy
        combined_text = f"{faq['question']} {faq['answer']}"
        embedding = model.encode(combined_text).tolist()
        
        # Create document
        doc = {
            "question_id": question_id,
            "question": faq['question'],
            "answer": faq['answer'],
            "category": category,
            "embedding": embedding,
            "created_at": datetime.utcnow().isoformat(),
            "added_by": "Migration Script"
        }
        
        documents.append(doc)
    
    # Insert all documents
    print(f"\n[6] Inserting {len(documents)} FAQs into MongoDB...")
    try:
        result = collection.insert_many(documents)
        print(f"    ✓ Inserted {len(result.inserted_ids)} documents")
    except Exception as e:
        print(f"    ✗ Error inserting documents: {e}")
        client.close()
        return
    
    # Verify insertion
    print(f"\n[7] Verifying insertion...")
    final_count = collection.count_documents({})
    print(f"    ✓ Final FAQ count: {final_count}")
    
    # Print category summary
    print(f"\n[8] Category Summary:")
    for category, count in sorted(category_counters.items(), key=lambda x: x[0]):
        print(f"    • {category}: {count} FAQs")
    
    client.close()
    
    print("\n" + "=" * 80)
    print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
    print("=" * 80)
    print(f"\nSummary:")
    print(f"  • Old FAQs removed: {current_count}")
    print(f"  • New FAQs added: {final_count}")
    print(f"  • Categories: {len(category_counters)}")
    print(f"  • Embedding model: {EMBEDDING_MODEL}")
    print(f"  • Database: {DB_NAME}.{COLLECTION_NAME}")
    print(f"  • Data source: {source}")


if __name__ == "__main__":
    main()
