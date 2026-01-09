#!/usr/bin/env python3
"""
Regenerate embeddings for all FAQs in MongoDB using BGE-large-en-v1.5
"""

import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Configuration
MONGODB_URI = os.getenv('MONGODB_URI')
DB_NAME = os.getenv('DB_NAME', "faq_bootcamp")
COLLECTION_NAME = os.getenv('COLLECTION_NAME', "questions")
EMBEDDING_MODEL = 'BAAI/bge-large-en-v1.5'

def main():
    print(f"Loading embedding model: {EMBEDDING_MODEL}")
    model = SentenceTransformer(EMBEDDING_MODEL)
    print("✓ Model loaded")
    
    print(f"\nConnecting to MongoDB...")
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]
    
    # Get all FAQs
    faqs = list(collection.find({}))
    print(f"✓ Found {len(faqs)} FAQs")
    
    print(f"\nGenerating embeddings...")
    for faq in tqdm(faqs, desc="Processing FAQs"):
        question = faq.get('question', '')
        if question:
            # Generate embedding
            embedding = model.encode(question).tolist()
            
            # Update in MongoDB
            collection.update_one(
                {'_id': faq['_id']},
                {'$set': {'embedding': embedding}}
            )
    
    client.close()
    print("\n✓ All embeddings regenerated successfully!")

if __name__ == "__main__":
    main()
