#!/usr/bin/env python3
"""
Admin MCP Server for FAQ Management
Provides administrative tools for adding FAQs, viewing recent additions, and exporting data
"""

import os
import asyncio
import base64
import secrets
from datetime import datetime
from typing import Optional, List, Dict, Any
from difflib import SequenceMatcher
import csv
from io import StringIO

from pymongo import MongoClient
from pydantic import BaseModel, Field
from fastmcp import FastMCP, Context
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# ============================================================================
# CONFIGURATION
# ============================================================================

MONGODB_URI = os.getenv('MONGODB_URI')
DB_NAME = os.getenv('DB_NAME', 'faq_bootcamp')
COLLECTION_NAME = os.getenv('COLLECTION_NAME', 'questions')
SERVER_HOST = os.getenv('SERVER_HOST', '0.0.0.0')
SERVER_PORT = int(os.getenv('ADMIN_SERVER_PORT', '9011'))

# Duplicate detection thresholds
FUZZY_THRESHOLD = 0.85
SEMANTIC_THRESHOLD = 0.90

# ============================================================================
# DATA MODELS
# ============================================================================

class AddFAQRequest(BaseModel):
    """Request model for adding a new FAQ."""
    question: str = Field(..., min_length=10, description="The FAQ question (minimum 10 characters)")
    answer: str = Field(..., min_length=20, description="The FAQ answer (minimum 20 characters)")
    category: str = Field(..., description="FAQ category")
    added_by: str = Field(..., description="Username or identifier of who is adding the FAQ")
    question_id: Optional[str] = Field(None, description="Optional question ID (auto-generated if not provided)")


class AddFAQResponse(BaseModel):
    """Response model for adding a new FAQ."""
    success: bool = Field(..., description="Whether the FAQ was added successfully")
    message: str = Field(..., description="Success or error message")
    question_id: Optional[str] = Field(None, description="The question ID of the added FAQ")
    faq: Optional[Dict[str, Any]] = Field(None, description="The complete FAQ document that was added")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_mongodb_collection():
    """Get MongoDB collection."""
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    db = client[DB_NAME]
    return db[COLLECTION_NAME], client


async def generate_question_id(category: str) -> str:
    """Generate a unique question ID based on category."""
    collection, client = get_mongodb_collection()
    
    try:
        # Get all FAQs in this category
        category_questions = list(collection.find(
            {"category": {"$regex": f"^{category}$", "$options": "i"}},
            {"question_id": 1}
        ))
        
        if not category_questions:
            # New category - find next category number
            all_faqs = list(collection.find({}, {"question_id": 1}))
            category_nums = set()
            for faq in all_faqs:
                qid = faq.get('question_id', '')
                if '.' in qid:
                    try:
                        cat_num = int(qid.split('.')[0].replace('Q', ''))
                        category_nums.add(cat_num)
                    except:
                        pass
            next_cat = max(category_nums) + 1 if category_nums else 1
            return f"Q{next_cat}.1"
        
        # Find highest question number in category
        max_num = 0
        category_num = None
        for faq in category_questions:
            qid = faq.get('question_id', '')
            if '.' in qid:
                try:
                    parts = qid.split('.')
                    cat_num = parts[0].replace('Q', '')
                    q_num = int(parts[1])
                    if category_num is None:
                        category_num = cat_num
                    max_num = max(max_num, q_num)
                except (ValueError, IndexError):
                    continue
        
        return f"Q{category_num}.{max_num + 1}"
    finally:
        client.close()


'''def generate_csv(data: List[Dict[str, Any]], columns: List[str]) -> str:
    """Generate CSV string from data."""
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()
    writer.writerows(data)
    return output.getvalue()'''


# ============================================================================
# FASTMCP SERVER
# ============================================================================

mcp = FastMCP("FAQ Admin Server")


@mcp.tool()
async def add_faq(
    question: str,
    answer: str,
    category: str,
    ctx: Context,
    added_by: str | None = None,
    question_id: str | None = None
) -> AddFAQResponse:
    """
    Add a new FAQ question-answer pair to the database.
    
    🔐 SECURITY: Session-Based Authentication
    This tool uses session-based authentication (standard MCP model):
    - Users configure the admin password in LibreChat's "Configure Variables"
    - This establishes an authenticated MCP session
    - All tool calls within that session are trusted
    - No password needed for individual tool calls
    
    The 'added_by' field is AUTOMATICALLY handled by the system.
    DO NOT ASK THE USER FOR 'added_by'.
    
    Args:
        question: The FAQ question (minimum 10 characters)
        answer: The FAQ answer (minimum 20 characters)
        category: FAQ category
        added_by: OPTIONAL. System automatically detects user. Do NOT ask user for this.
        question_id: Optional question ID (auto-generated if not provided)
    
    Returns:
        AddFAQResponse with success status
    """
    # 0. Password Validation via Header
    # LibreChat passes user-configured password via X-Admin-Password header (customUserVars)
    expected_password = os.getenv('ADMIN_PASSWORD')
    
    if not expected_password:
        return AddFAQResponse(
            success=False,
            message="Error: Admin password is not configured on the server. Please contact the administrator."
        )
    
    # Extract password from request headers
    provided_password = None
    try:
        req_ctx = getattr(ctx, 'request_context', None)
        if req_ctx and hasattr(req_ctx, 'request'):
            request = req_ctx.request
            # Extract the raw header value
            raw_password = (
                request.headers.get('x-user-m-key') or         # New variable M_KEY (prefix x-user-)
                request.headers.get('x-user-password') or      # Old variable fallback
                request.headers.get('x-admin-password') or 
                request.headers.get('X-Admin-Password')
            )
            
            # Check if it's actually set and not the literal template string from LibreChat
            # LibreChat sends literal "{{VAR_NAME}}" if the user hasn't configured it.
            if raw_password and not (raw_password.startswith("{{") and raw_password.endswith("}}")):
                provided_password = raw_password.strip()
            else:
                provided_password = None
            
            print("=" * 80)
            print(f"DEBUG: Authentication Check")
            print(f"DEBUG: Expected: {expected_password}")
            print(f"DEBUG: Raw Header Value: {raw_password}")
            print(f"DEBUG: Interpolated Password: {'***' if provided_password else 'None'}")
            print("=" * 80)
    except Exception as e:
        print(f"ERROR: Failed to extract password: {e}")
    
    unified_error_message = (
        "I’m sorry—I wasn’t able to add the FAQ because the system’s admin authentication didn’t succeed. "
        "This usually means the admin password stored in the “Configure Variables” settings is missing or incorrect.\n\n"
        "If you’re an admin, please double‑check the password you set for the MCP admin server and try again. "
        "Once the credentials are valid, the new FAQ will be added successfully. Let me know if there’s anything else I can help with!"
    )
    
    # Case 1: Password is not set (Missing or Literal Template)
    if not provided_password:
        return AddFAQResponse(
            success=False,
            message=unified_error_message
        )
    
    # Case 2: Incorrect Password
    import secrets
    if not secrets.compare_digest(provided_password, expected_password):
        print(f"DEBUG: Auth FAILED - mismatch")
        return AddFAQResponse(
            success=False,
            message=unified_error_message
        )
    
    print(f"DEBUG: Auth SUCCESS")
    # Password validated - proceed with adding FAQ

        
    # 1. Try to use the explicitly provided added_by if present
    # (LLM might still pass it if user explicitly said "Added by X")
    final_added_by = added_by

    # 2. If not provided, try to extract from context (Headers or Meta)
    if not final_added_by:
        try:
            # Check Headers first (injected via LibreChat config)
            req_ctx = getattr(ctx, 'request_context', None)
            if req_ctx and hasattr(req_ctx, 'headers'):
                headers = req_ctx.headers
                # Headers are usually case-insensitive or lowercased
                final_added_by = (
                    headers.get('x-user-name') or
                    headers.get('x-user-email') or
                    headers.get('x-user-id')
                )
                print(f"DEBUG: Extracted from headers: {final_added_by}")

            # Fallback to direct meta if headers didn't work
            if not final_added_by and hasattr(ctx, 'meta') and ctx.meta:
                # Prioritize Name -> Email -> User ID
                final_added_by = (
                    ctx.meta.get('name') or 
                    ctx.meta.get('email') or 
                    ctx.meta.get('username') or 
                    ctx.meta.get('user_id') or 
                    ctx.meta.get('client_id')
                )
        except Exception as e:
            print(f"Error extracting user context: {e}")

    # 3. Final Fallback
    if not final_added_by:
        final_added_by = os.getenv('DEFAULT_ADMIN_USER', 'admin')

    # Input validation
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
    
    if not final_added_by or not str(final_added_by).strip():
        return AddFAQResponse(
            success=False,
            message="Could not determine user identity (added_by). Please ensure you are logged in."
        )
    
    collection, client = get_mongodb_collection()
    
    try:
        # Check for exact duplicate
        existing = collection.find_one({"question": question.strip()})
        if existing:
            return AddFAQResponse(
                success=False,
                message=f"A FAQ with this exact question already exists (ID: {existing.get('question_id')})"
            )
        
        # Check for fuzzy matching duplicates
        all_faqs = list(collection.find({}, {"question": 1, "question_id": 1}))
        for faq in all_faqs:
            existing_question = faq.get('question', '')
            similarity = SequenceMatcher(
                None,
                question.strip().lower(),
                existing_question.lower()
            ).ratio()
            
            if similarity > FUZZY_THRESHOLD:
                return AddFAQResponse(
                    success=False,
                    message=f"A very similar question already exists (ID: {faq.get('question_id')}, {similarity*100:.1f}% similar): '{existing_question}'"
                )
        
        # Generate question ID if not provided
        if not question_id:
            question_id = await generate_question_id(category.strip())
        
        # Create FAQ document
        faq_doc = {
            "question_id": question_id,
            "question": question.strip(),
            "answer": answer.strip(),
            "category": category.strip(),
            "added_by": str(final_added_by).strip(),
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Insert into MongoDB
        result = collection.insert_one(faq_doc.copy())
        faq_doc.pop('_id', None)  # Remove MongoDB ID for response
        
        return AddFAQResponse(
            success=True,
            message=f"FAQ successfully added with ID: {question_id}",
            question_id=question_id,
            faq=faq_doc
        )
    
    except Exception as e:
        return AddFAQResponse(
            success=False,
            message=f"Error adding FAQ: {str(e)}"
        )
    finally:
        client.close()


# @mcp.tool()
# async def last_n(n: int = 10) -> str:
#     """
#     Get the last n FAQs added to the database as CSV.
#     
#     Returns a CSV string with columns: Question, Answer, Added By
#     The FAQs are sorted by creation date (most recent first).
#     
#     Args:
#         n: Number of recent FAQs to retrieve (default: 10, max: 100)
#     
#     Returns:
#         CSV string with Question, Answer, and Added By columns
#     """
#     # Validate n
#     if n < 1:
#         n = 1
#     elif n > 100:
#         n = 100
#     
#     collection, client = get_mongodb_collection()
#     
#     try:
#         # Get last n FAQs sorted by created_at descending
#         faqs = list(collection.find(
#             {},
#             {"question": 1, "answer": 1, "added_by": 1, "created_at": 1}
#         ).sort("created_at", -1).limit(n))
#         
#         # Prepare data for CSV
#         csv_data = []
#         for faq in faqs:
#             csv_data.append({
#                 "Question": faq.get("question", ""),
#                 "Answer": faq.get("answer", ""),
#                 "Added By": faq.get("added_by", "system")
#             })
#         
#         # Generate CSV
#         if not csv_data:
#             return "No FAQs found in database"
#         
#         # Save to file instead of returning string
#         timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
#         filename = f"recent_{n}_faqs_{timestamp}.csv"
#         file_path = os.path.join("/app/downloads", filename)
#         
#         # Ensure directory exists
#         os.makedirs(os.path.dirname(file_path), exist_ok=True)
#         
#         # Save to file instead of returning string
#         timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
#         filename = f"recent_{n}_faqs_{timestamp}.csv"
#         file_path = os.path.join("/app/downloads", filename)
#         
#         # Ensure directory exists
#         os.makedirs(os.path.dirname(file_path), exist_ok=True)
#         
#         with open(file_path, 'w', newline='') as f:
#             writer = csv.DictWriter(f, fieldnames=["Question", "Answer", "Added By"])
#             writer.writeheader()
#             writer.writerows(csv_data)
#         
#         return f"File generated successfully: [Download CSV](/images/downloads/{filename})"
#     
#     except Exception as e:
#         return f"Error retrieving FAQs: {str(e)}"
#     finally:
#         client.close()


# @mcp.tool()
# async def download_data() -> str:
#     """
#     Download all FAQ data from MongoDB as CSV.
#     
#     Exports all FAQs with all fields including:
#     - Question ID
#     - Question
#     - Answer
#     - Category
#     - Added By
#     - Created At
#     
#     Returns:
#         Link to download containing all FAQ data
#     """
#     collection, client = get_mongodb_collection()
#     
#     try:
#         # Get all FAQs
#         faqs = list(collection.find(
#             {},
#             {
#                 "question_id": 1,
#                 "question": 1,
#                 "answer": 1,
#                 "category": 1,
#                 "added_by": 1,
#                 "created_at": 1
#             }
#         ).sort("question_id", 1))
#         
#         # Prepare data for CSV
#         csv_data = []
#         for faq in faqs:
#             csv_data.append({
#                 "Question ID": faq.get("question_id", ""),
#                 "Question": faq.get("question", ""),
#                 "Answer": faq.get("answer", ""),
#                 "Category": faq.get("category", ""),
#                 "Added By": faq.get("added_by", "system"),
#                 "Created At": faq.get("created_at", "")
#             })
#         
#         # Generate CSV
#         if not csv_data:
#             return "No FAQs found in database"
#         
#         columns = ["Question ID", "Question", "Answer", "Category", "Added By", "Created At"]
#         
#         # Save to file
#         timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
#         filename = f"all_faqs_{timestamp}.csv"
#         file_path = os.path.join("/app/downloads", filename)
#         
#         # Ensure directory exists
#         os.makedirs(os.path.dirname(file_path), exist_ok=True)
#         
#         # Save to file
#         timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
#         filename = f"all_faqs_{timestamp}.csv"
#         file_path = os.path.join("/app/downloads", filename)
#         
#         # Ensure directory exists
#         os.makedirs(os.path.dirname(file_path), exist_ok=True)
#         
#         with open(file_path, 'w', newline='') as f:
#             writer = csv.DictWriter(f, fieldnames=columns)
#             writer.writeheader()
#             writer.writerows(csv_data)
#         
#         return f"File generated successfully: [Download CSV](/images/downloads/{filename})"
#     
#     except Exception as e:
#         return f"Error downloading data: {str(e)}"
#     finally:
#         client.close()
# 
# 
# from fastmcp import Context
# 
# @mcp.tool()
# async def debug_context(ctx: Context) -> str:
#     """
#     Debug tool to inspect the MCP request context.
#     Returns the string representation of the context.
#     """
#     context_info = []
#     
#     # Inspect context attributes
#     for attr in dir(ctx):
#         if not attr.startswith('_'):
#             try:
#                 val = getattr(ctx, attr)
#                 context_info.append(f"{attr}: {val}")
#             except Exception as e:
#                 context_info.append(f"{attr}: <error: {e}>")
#     
#     # Try to access session/client info specifically if available
#     try:
#         if hasattr(ctx, 'session'):
#              context_info.append(f"Session: {ctx.session}")
#         if hasattr(ctx, 'meta'):
#              context_info.append(f"Meta: {ctx.meta}")
#     except:
#         pass
#         
#     return "\n".join(context_info)


# ============================================================================
# SERVER STARTUP
# ============================================================================

if __name__ == "__main__":
    print(f"\n🚀 Starting FAQ Admin MCP Server on http://{SERVER_HOST}:{SERVER_PORT}")
    print("=" * 60)
    print("🔐 Password Protection: ENABLED (MCP Connection Level)")
    print("Available tools:")
    print("  - add_faq: Add new FAQ with user tracking")
    print("  # - last_n: Get last n FAQs as CSV (Disabled)")
    print("  # - download_data: Export all FAQs as CSV (Disabled)")
    print("  # - debug_context: Inspect request context (Disabled)")
    print("=" * 60)
    print("\n⚠️  Note: Password validation at MCP configuration level")
    print(f"    LibreChat must provide correct password when configuring server\n")
    
    # Run the MCP server with streamable-http transport
    mcp.run(
        transport='streamable-http',
        host=SERVER_HOST,
        port=SERVER_PORT
    )


