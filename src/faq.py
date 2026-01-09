"""
FAQ MCP Server using FastMCP
Consolidated single-file implementation.
"""

import os
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any
from urllib.parse import quote_plus
from datetime import datetime
from difflib import SequenceMatcher

import numpy as np
import pymongo
from pymongo import MongoClient
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from fastmcp import FastMCP
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ============================================================================
# CONSTANTS & CONFIGURATION
# ============================================================================

# Load environment variables
# Look for .env in the same directory as this file
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# MongoDB Configuration
MONGODB_URI = os.getenv('MONGODB_URI')
# Fallback for development if env var is missing, though constants.py raised error
if not MONGODB_URI:
    # Attempt to construct from user/pass if provided separately
    _user = os.getenv("MONGO_INITDB_ROOT_USERNAME", "agriai")
    _pass = os.getenv("MONGO_INITDB_ROOT_PASSWORD", "agriai1224")
    # This is a fallback default from the original ajrasakha/mcp/faq.py pattern
    # But constants.py raised ValueError. We'll warn instead of failing immediately to allow import.
    print("Warning: MONGODB_URI not set.")

DB_NAME = os.getenv('DB_NAME', "faq_bootcamp")
COLLECTION_NAME = os.getenv('COLLECTION_NAME', "questions")

# Embedding Configuration
EMBEDDING_PROVIDER = os.getenv('EMBEDDING_PROVIDER', 'local')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
# Use BGE-large-en-v1.5 as default embedding model
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'BAAI/bge-large-en-v1.5')
EMBEDDING_DIMENSION = int(os.getenv('EMBEDDING_DIMENSION', '1024'))

# Local embedding model (for sentence-transformers)
LOCAL_EMBEDDING_MODEL = os.getenv('LOCAL_EMBEDDING_MODEL', 'BAAI/bge-large-en-v1.5')

# Search Configuration
TFIDF_WEIGHT = float(os.getenv('TFIDF_WEIGHT', '0.3'))
EMBEDDING_WEIGHT = float(os.getenv('EMBEDDING_WEIGHT', '0.7'))
DEFAULT_TOP_K = 3
MAX_TOP_K = 5

# Server Configuration
SERVER_HOST = os.getenv('SERVER_HOST', '0.0.0.0')
SERVER_PORT = int(os.getenv('SERVER_PORT', '9010'))
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')


# ============================================================================
# MODELS
# ============================================================================

class FAQMetadata(BaseModel):
    """Metadata for a single FAQ result."""
    question_id: str = Field(..., description="Unique FAQ identifier (e.g., Q1.1)")
    category: str = Field(..., description="FAQ category")
    similarity_score: float = Field(..., description="Overall similarity score (0-1)")
    tfidf_score: float = Field(0.0, description="TF-IDF similarity score (0-1)")
    embedding_score: float = Field(0.0, description="Embedding similarity score (0-1)")
    search_method: str = Field("tfidf", description="Search method used")


class FAQResult(BaseModel):
    """Single FAQ search result."""
    question: str = Field(..., description="The FAQ question")
    answer: str = Field(..., description="The FAQ answer")
    metadata: FAQMetadata = Field(..., description="Result metadata")


class SearchRequest(BaseModel):
    """Request model for FAQ search."""
    query: str = Field(..., description="User's question")
    top_k: int = Field(3, ge=1, le=5, description="Number of results to return")


class SearchResponse(BaseModel):
    """Response model for FAQ search."""
    results: List[FAQResult] = Field(..., description="List of FAQ results")
    total_results: int = Field(..., description="Total number of results found")
    search_method: str = Field(..., description="Search method used")


class AddFAQRequest(BaseModel):
    """Request model for adding a new FAQ."""
    question: str = Field(..., min_length=10, description="The FAQ question (minimum 10 characters)")
    answer: str = Field(..., min_length=20, description="The FAQ answer (minimum 20 characters)")
    category: str = Field(..., description="FAQ category (e.g., 'Program Overview', 'Eligibility & Registration')")
    question_id: Optional[str] = Field(None, description="Optional question ID (auto-generated if not provided)")


class AddFAQResponse(BaseModel):
    """Response model for adding a new FAQ."""
    success: bool = Field(..., description="Whether the FAQ was added successfully")
    message: str = Field(..., description="Success or error message")
    question_id: Optional[str] = Field(None, description="The question ID of the added FAQ")
    faq: Optional[Dict[str, Any]] = Field(None, description="The complete FAQ document that was added")


# ============================================================================
# GLOBAL STATE & UTILITIES
# ============================================================================

# Global caches
_faq_cache = []
_vectorizer = None
_tfidf_matrix = None
_embedding_function = None


def get_embedding_function():
    """Get the appropriate embedding function based on configuration."""
    global _embedding_function
    
    if _embedding_function is not None:
        return _embedding_function
    
    if EMBEDDING_PROVIDER == "openai":
        try:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)
            
            def embed_text(text: str) -> List[float]:
                response = client.embeddings.create(
                    model=EMBEDDING_MODEL,
                    input=text
                )
                return response.data[0].embedding
            
            _embedding_function = embed_text
        except ImportError:
            print("Error: OpenAI client not installed. Install with `pip install openai`.")
            raise
    
    elif EMBEDDING_PROVIDER == "anthropic":
        try:
            import voyageai
            vo = voyageai.Client(api_key=ANTHROPIC_API_KEY)
            
            def embed_text(text: str) -> List[float]:
                # Using voyage-2 as per original code
                result = vo.embed([text], model="voyage-2")
                return result.embeddings[0]
            
            _embedding_function = embed_text
        except ImportError:
            print("Error: VoyageAI client not installed. Install with `pip install voyageai`.")
            raise
    
    elif EMBEDDING_PROVIDER == "local":
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer(LOCAL_EMBEDDING_MODEL)
            
            def embed_text(text: str) -> List[float]:
                embedding = model.encode(text)
                return embedding.tolist()
            
            _embedding_function = embed_text
        except ImportError:
            print("Error: sentence-transformers not installed. Install with `pip install sentence-transformers`.")
            raise
    else:
        # Default or fallback
        print(f"Warning: Unknown embedding provider '{EMBEDDING_PROVIDER}'. Using dummy embedding.")
        def dummy_embed(text: str) -> List[float]:
            return [0.0] * EMBEDDING_DIMENSION
        _embedding_function = dummy_embed
    
    return _embedding_function


def invalidate_caches():
    """Invalidate all caches to force reload of FAQs."""
    global _faq_cache, _vectorizer, _tfidf_matrix
    _faq_cache = []
    _vectorizer = None
    _tfidf_matrix = None
    print("✓ Caches invalidated")


async def generate_question_id(category: str) -> str:
    """
    Generate a unique question ID based on category.
    Format: Q{category_num}.{question_num}
    """
    if not _faq_cache:
        await load_faqs_from_mongodb()
    
    # Extract category questions from existing FAQs
    category_questions = [
        faq for faq in _faq_cache 
        if faq.get('category', '').lower() == category.lower()
    ]
    
    if not category_questions:
        # New category, start with Q1.1
        return "Q1.1"
    
    # Find the highest question number in this category
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
    
    # Get category number from first question
    first_qid = category_questions[0].get('question_id', 'Q1.1')
    category_num = first_qid.split('.')[0].replace('Q', '')
    
    return f"Q{category_num}.{max_num + 1}"


async def load_faqs_from_mongodb() -> List[dict]:
    """Load all FAQs from MongoDB and cache them."""
    global _faq_cache
    
    if _faq_cache:
        return _faq_cache
    
    if not MONGODB_URI:
        print("Error: MONGODB_URI not set. Cannot load FAQs.")
        return []

    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        # Test connection
        client.server_info()
        
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]
        
        _faq_cache = list(collection.find({}, {'_id': 0}))
        client.close()
        
        print(f"✓ Connected to MongoDB: {DB_NAME}.{COLLECTION_NAME}")
        print(f"✓ Loaded {len(_faq_cache)} FAQs")
        
        return _faq_cache
    except Exception as e:
        print(f"✗ Failed to load FAQs from MongoDB: {e}")
        return []


async def build_tfidf_index():
    """Build TF-IDF index for all questions."""
    global _vectorizer, _tfidf_matrix, _faq_cache
    
    if _vectorizer is not None and _tfidf_matrix is not None:
        return
    
    if not _faq_cache:
        await load_faqs_from_mongodb()
        
    if not _faq_cache:
        print("Warning: No FAQs loaded to build TF-IDF index.")
        return
    
    questions = [faq.get('question', '') for faq in _faq_cache]
    
    _vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words='english',
        ngram_range=(1, 2),
        max_features=1000
    )
    
    _tfidf_matrix = _vectorizer.fit_transform(questions)
    print("✓ TF-IDF index built")


async def search_tfidf(query: str) -> np.ndarray:
    """Search using TF-IDF only."""
    global _vectorizer, _tfidf_matrix
    
    if _vectorizer is None or _tfidf_matrix is None:
        await build_tfidf_index()
    
    if _vectorizer is None:
        return np.array([])
        
    query_vector = _vectorizer.transform([query])
    similarities = cosine_similarity(query_vector, _tfidf_matrix)[0]
    
    return similarities


async def search_embedding(query: str) -> Optional[np.ndarray]:
    """Search using embeddings."""
    global _faq_cache
    
    if not _faq_cache:
        await load_faqs_from_mongodb()
    
    # Check if embeddings exist
    if not any('embedding' in faq for faq in _faq_cache):
        return None
    
    try:
        embed_fn = get_embedding_function()
        query_embedding = np.array(embed_fn(query))
        
        faq_embeddings = []
        for faq in _faq_cache:
            if 'embedding' in faq:
                faq_embeddings.append(faq['embedding'])
            else:
                faq_embeddings.append([0.0] * len(query_embedding))
        
        faq_embeddings = np.array(faq_embeddings)
        similarities = cosine_similarity([query_embedding], faq_embeddings)[0]
        
        return similarities
    
    except Exception as e:
        print(f"Error in embedding search: {e}")
        return None


async def search_faqs(query: str, top_k: int = 3) -> List[FAQResult]:
    """
    Hybrid search combining TF-IDF and embeddings.
    """
    global _faq_cache
    
    if not _faq_cache:
        await load_faqs_from_mongodb()
        
    if not _faq_cache:
        return []
    
    # Get TF-IDF scores
    tfidf_scores = await search_tfidf(query)
    if len(tfidf_scores) == 0:
        tfidf_scores = np.zeros(len(_faq_cache))
    
    # Get embedding scores
    embedding_scores = await search_embedding(query)
    
    # Combine scores
    if embedding_scores is not None:
        combined_scores = (
            TFIDF_WEIGHT * tfidf_scores +
            EMBEDDING_WEIGHT * embedding_scores
        )
        search_method = "hybrid"
    else:
        combined_scores = tfidf_scores
        search_method = "tfidf"
    
    # Get top K indices
    top_indices = np.argsort(combined_scores)[::-1][:top_k]
    
    # Build results
    results = []
    for idx in top_indices:
        score = combined_scores[idx]
        if score > 0:
            faq = _faq_cache[idx]
            
            metadata = FAQMetadata(
                question_id=faq.get('question_id', 'unknown'),
                category=faq.get('category', 'general'),
                similarity_score=float(score),
                tfidf_score=float(tfidf_scores[idx]) if len(tfidf_scores) > 0 else 0.0,
                embedding_score=float(embedding_scores[idx]) if embedding_scores is not None else 0.0,
                search_method=search_method
            )
            
            result = FAQResult(
                question=faq.get('question', ''),
                answer=faq.get('answer', ''),
                metadata=metadata
            )
            
            results.append(result)
    
    return results


async def initialize():
    """Initialize the search system."""
    print("Initializing FAQ search system...")
    await load_faqs_from_mongodb()
    await build_tfidf_index()
    
    has_embeddings = any('embedding' in faq for faq in _faq_cache)
    if has_embeddings:
        print(f"✓ Loaded {len(_faq_cache)} FAQs with embeddings")
    else:
        print(f"✓ Loaded {len(_faq_cache)} FAQs (TF-IDF only)")
        
    print("✓ Initialization complete")


# ============================================================================
# MCP SERVER
# ============================================================================

# Initialize FastMCP server
mcp = FastMCP("FAQ Search Server")


@mcp.tool()
async def search_faq(query: str, top_k: int = 3) -> List[FAQResult]:
    """
    Search the FAQ database for answers to user questions.
    
    Uses hybrid search combining keyword matching (TF-IDF) and 
    semantic understanding (embeddings) for accurate results.
    
    The query should:
    - Be a clear, concise question about the bootcamp or internship
    - Focus on topics like registration, ViBe platform, attendance, certification
    - Avoid meta-instructions (e.g., "use this tool", "search the database")
    
    Args:
        query: User's question about the Full Stack Development Bootcamp or NPTEL Internship
        top_k: Number of results to return (default: 3, max: 5)
    
    Returns:
        List of FAQ results with questions, answers, and metadata including similarity scores
    """
    # Validate top_k
    if top_k < 1:
        top_k = 1
    elif top_k > 5:
        top_k = 5
    
    # Perform search
    results = await search_faqs(query, top_k)
    
    return results


@mcp.tool()
async def add_faq(
    question: str,
    answer: str,
    category: str,
    question_id: Optional[str] = None
) -> AddFAQResponse:
    """
    Add a new FAQ question-answer pair to the database.
    
    This tool is designed for admin users to add new FAQ entries to the system.
    The FAQ will be validated, assigned an ID, embedded, and stored in MongoDB.
    
    Duplicate detection uses three methods:
    1. Exact matching (case-sensitive)
    2. Fuzzy matching (85% threshold using difflib)
    3. Semantic similarity (90% threshold using embeddings)
    
    Args:
        question: The FAQ question (minimum 10 characters)
        answer: The FAQ answer (minimum 20 characters)
        category: FAQ category (e.g., 'Program Overview', 'ViBe Platform')
        question_id: Optional custom question ID (auto-generated if not provided)
    
    Returns:
        AddFAQResponse with success status, message, and the added FAQ details
    
    Example:
        add_faq(
            question="How do I reset my password?",
            answer="To reset your password, click on 'Forgot Password' on the login page...",
            category="ViBe Platform"
        )
    """
    # Validate inputs
    if len(question.strip()) < 10:
        return AddFAQResponse(
            success=False,
            message="Question must be at least 10 characters long"
        )
    
    if len(answer.strip()) < 20:
        return AddFAQResponse(
            success=False,
            message="Answer must be at least 20 characters long"
        )
    
    if not category.strip():
        return AddFAQResponse(
            success=False,
            message="Category is required"
        )
    
    # Check MongoDB connection
    if not MONGODB_URI:
        return AddFAQResponse(
            success=False,
            message="MongoDB connection not configured"
        )
    
    try:
        # Connect to MongoDB
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        client.server_info()  # Test connection
        
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]
        
        # Check for duplicate question using fuzzy matching and semantic similarity
        # 1. Exact match check
        existing = collection.find_one({"question": question.strip()})
        if existing:
            client.close()
            return AddFAQResponse(
                success=False,
                message=f"A FAQ with this exact question already exists (ID: {existing.get('question_id', 'unknown')})"
            )
        
        # 2. Fuzzy matching check (using difflib)
        FUZZY_THRESHOLD = 0.85  # 85% similarity threshold
        
        all_faqs = list(collection.find({}, {'question': 1, 'question_id': 1}))
        for faq in all_faqs:
            existing_question = faq.get('question', '')
            similarity = SequenceMatcher(None, question.strip().lower(), existing_question.lower()).ratio()
            if similarity > FUZZY_THRESHOLD:
                client.close()
                return AddFAQResponse(
                    success=False,
                    message=f"A very similar question already exists (ID: {faq.get('question_id', 'unknown')}, {similarity*100:.1f}% similar): '{existing_question}'"
                )
        
        # 3. Semantic similarity check (using embeddings)
        SEMANTIC_THRESHOLD = 0.90  # 90% semantic similarity threshold
        
        try:
            embed_fn = get_embedding_function()
            new_question_embedding = np.array(embed_fn(question.strip()))
            
            # Check against all existing questions with embeddings
            for faq in all_faqs:
                faq_full = collection.find_one({'_id': faq['_id']})
                if faq_full and 'embedding' in faq_full:
                    existing_embedding = np.array(faq_full['embedding'])
                    semantic_similarity = cosine_similarity([new_question_embedding], [existing_embedding])[0][0]
                    
                    if semantic_similarity > SEMANTIC_THRESHOLD:
                        client.close()
                        return AddFAQResponse(
                            success=False,
                            message=f"A semantically similar question already exists (ID: {faq.get('question_id', 'unknown')}, {semantic_similarity*100:.1f}% similar): '{faq.get('question', '')}'"
                        )
        except Exception as e:
            print(f"Warning: Semantic similarity check failed: {e}")
            # Continue without semantic check if it fails
        
        # Generate question ID if not provided
        if not question_id:
            question_id = await generate_question_id(category.strip())
        
        # Generate embedding for the question
        try:
            embed_fn = get_embedding_function()
            embedding = embed_fn(question.strip())
        except Exception as e:
            print(f"Warning: Failed to generate embedding: {e}")
            embedding = None
        
        # Create FAQ document
        faq_doc = {
            "question_id": question_id,
            "question": question.strip(),
            "answer": answer.strip(),
            "category": category.strip(),
            "created_at": datetime.utcnow().isoformat(),
        }
        
        if embedding:
            faq_doc["embedding"] = embedding
        
        # Insert into MongoDB
        result = collection.insert_one(faq_doc)
        
        # Remove MongoDB _id for response
        faq_doc.pop('_id', None)
        
        client.close()
        
        # Invalidate caches so new FAQ is immediately searchable
        invalidate_caches()
        
        return AddFAQResponse(
            success=True,
            message=f"FAQ successfully added with ID: {question_id}",
            question_id=question_id,
            faq=faq_doc
        )
        
    except pymongo.errors.ConnectionFailure as e:
        return AddFAQResponse(
            success=False,
            message=f"Failed to connect to MongoDB: {str(e)}"
        )
    except Exception as e:
        return AddFAQResponse(
            success=False,
            message=f"Error adding FAQ: {str(e)}"
        )


if __name__ == "__main__":
    # Initialize search system
    asyncio.run(initialize())
    
    # Run server
    print(f"\n🚀 Starting FAQ MCP Server on http://{SERVER_HOST}:{SERVER_PORT}")
    print("=" * 60)
    mcp.run(transport='streamable-http', host=SERVER_HOST, port=SERVER_PORT)
