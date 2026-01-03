# FAQ MCP Server

Intelligent FAQ search system using FastMCP framework with hybrid TF-IDF and semantic embeddings.

## Features

- 🔍 **Hybrid Search**: TF-IDF + semantic embeddings
- 🤖 **Multi-Provider**: OpenAI, Anthropic, or local embeddings
- 📊 **54 FAQs**: Bootcamp, ViBe platform, attendance, certification
- ⚡ **FastMCP**: Clean architecture with HTTP API
- � **Port 9010**: Streamable-HTTP transport

## Quick Start

### 1. Setup

```bash
git clone <repository-url>
cd Bootcamp-mcp
python3 -m venv venv
source venv/bin/activate
pip install -r mcp-server/requirements.txt
```

### 2. Configure

```bash
cp mcp-server/.env.example .env
# Edit .env with your MongoDB URI and API keys
```

### 3. Ingest Data

```bash
python scripts/parse_faq.py
python scripts/ingest_to_mongodb.py
python scripts/generate_embeddings.py  # Optional
```

### 4. Run

```bash
./run_server.sh
# Or: python mcp-server/server.py
```

Server starts on `http://localhost:9010`

### 5. Test

```bash
./test_server.sh
# Or: python mcp-server/test_mcp_tool.py
```

## Project Structure

```
Bootcamp-mcp/
├── FAQ Data/
│   └── Unified_FAQ.txt          # 54 FAQ entries
├── scripts/
│   ├── parse_faq.py             # Parse FAQ file
│   ├── ingest_to_mongodb.py     # Ingest to MongoDB
│   └── generate_embeddings.py   # Generate embeddings
├── mcp-server/
│   ├── server.py                # FastMCP server
│   ├── functions.py             # Search logic
│   ├── models.py                # Pydantic models
│   ├── constants.py             # Configuration
│   ├── test_mcp_tool.py         # Test script
│   ├── test_fastmcp.py          # Unit tests
│   ├── requirements.txt         # Dependencies
│   └── .env.example             # Config template
├── run_server.sh                # Run server
├── test_server.sh               # Test server
└── README.md                    # This file
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MONGODB_URI` | - | MongoDB connection (required) |
| `EMBEDDING_PROVIDER` | `openai` | openai, anthropic, or local |
| `OPENAI_API_KEY` | - | For OpenAI embeddings |
| `TFIDF_WEIGHT` | `0.3` | TF-IDF weight (0-1) |
| `EMBEDDING_WEIGHT` | `0.7` | Embedding weight (0-1) |
| `SERVER_PORT` | `9010` | Server port |

### Embedding Providers

- **OpenAI**: Best quality, $0.02/1M tokens
- **Anthropic**: Similar quality and pricing
- **Local**: Free, offline, good quality

## Usage

### MCP Tool

The server exposes a `search_faq` tool:

```python
search_faq(query: str, top_k: int = 3) -> List[FAQResult]
```

**Example queries:**
- "How do I register?"
- "Can I use mobile for ViBe?"
- "What are the attendance requirements?"

### With MCP Clients

Connect via Claude Desktop or other MCP clients to `http://localhost:9010/mcp`

## How It Works

**Hybrid Search:**
```
Final Score = (0.3 × TF-IDF) + (0.7 × Embeddings)
```

**Example:**
- Query: "What's the sign-up process?"
- TF-IDF: 25% (different words)
- Embedding: 92% (same meaning)
- **Final: 72%** ✅

## Commands

```bash
# Run server
./run_server.sh

# Test server
./test_server.sh

# Stop server
pkill -f "mcp-server/server.py"

# Update FAQs
python scripts/parse_faq.py
python scripts/ingest_to_mongodb.py
python scripts/generate_embeddings.py
```

## FAQ Categories

54 FAQs across 12 categories:
1. Program Overview (3)
2. Eligibility & Registration (5)
3. Dates, Duration & Schedule (4)
4. Mode of Delivery & Attendance (20)
5. Course Content & Learning (2)
6. Projects & Assignments (2)
7. Mentorship & Guidance (2)
8. Support & Issue Resolution (6)
9. Completion Criteria & Certification (3)
10. Stipend & Recommendation Letters (3)
11. Termination & Rejoining Policy (3)
12. GitHub Assignment Submission (1)

## License

MIT License

Created for VLED, Indian Institute of Technology, Ropar

## Support

- **Email**: internship-support@vicharanashala.zohodesk.in
- **DLED Team**: dled@iitrpr.ac.in

## Tech Stack

FastMCP • MongoDB • OpenAI/Anthropic/Local Embeddings • Pydantic • Python 3.12+
