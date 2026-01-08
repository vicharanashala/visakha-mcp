# FAQ MCP Server

[![Docker Hub Publish](https://github.com/vicharanashala/faq-mcp-server/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/vicharanashala/faq-mcp-server/actions/workflows/docker-publish.yml)
[![Docker Hub](https://img.shields.io/docker/v/vicharanashala/faq-mcp-server?label=Docker%20Hub)](https://hub.docker.com/r/vicharanashala/faq-mcp-server)

Intelligent FAQ search system using FastMCP framework with hybrid TF-IDF and semantic embeddings.

## Features

- 🔍 **Hybrid Search**: TF-IDF + semantic embeddings
- 🤖 **BGE Embeddings**: BAAI/bge-large-en-v1.5 (1024 dimensions)
- 📊 **54 FAQs**: Bootcamp, ViBe platform, attendance, certification
- ⚡ **FastMCP**: Clean architecture with HTTP API
- 🐳 **Dockerized**: Easy deployment with Docker Compose
- 🔌 **Port 9010**: Streamable-HTTP transport

## Quick Start

### Using Docker (Recommended)

```bash
# Start the server
docker compose up -d

# View logs
docker logs faq-mcp-server -f

# Stop the server
docker compose down
```

### Manual Setup

```bash
# Install dependencies
pip install -r requirements.txt sentence-transformers

# Configure environment
cp .env.example .env
# Edit .env with your MongoDB URI

# Run the server
python faq.py
```

## Docker Hub Deployment

### Using Pre-built Image

Pull and run the latest image from Docker Hub:

```bash
# Pull the latest image
docker pull vicharanashala/faq-mcp-server:latest

# Run with environment variables
docker run -d \
  --name faq-mcp-server \
  -p 9010:9010 \
  -e MONGODB_URI="your-mongodb-connection-string" \
  -e DB_NAME="faq_bootcamp" \
  -e COLLECTION_NAME="questions" \
  vicharanashala/faq-mcp-server:latest

# View logs
docker logs faq-mcp-server -f
```

### Available Tags

- `latest` - Most recent build from main branch
- `v1.0.0`, `v1.0`, `v1` - Semantic version tags
- `main-<sha>` - Specific commit builds

### Multi-Platform Support

Images are available for:
- `linux/amd64` (x86_64)
- `linux/arm64` (ARM64/Apple Silicon)

### Automated Deployment

This project uses GitHub Actions for automated Docker Hub deployment:

1. **Tag-based Release**: Push a version tag to trigger deployment
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

2. **Manual Trigger**: Use GitHub Actions workflow dispatch

#### Required GitHub Secrets

To enable automated deployment, configure these secrets in your GitHub repository:

| Secret | Description |
|--------|-------------|
| `DOCKERHUB_USERNAME` | Your Docker Hub username |
| `DOCKERHUB_TOKEN` | Docker Hub access token ([create here](https://hub.docker.com/settings/security)) |

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MONGODB_URI` | - | MongoDB connection (required) |
| `DB_NAME` | `faq_bootcamp` | Database name |
| `COLLECTION_NAME` | `questions` | Collection name |
| `EMBEDDING_PROVIDER` | `local` | Embedding provider (local/openai/anthropic) |
| `EMBEDDING_MODEL` | `BAAI/bge-large-en-v1.5` | Embedding model |
| `EMBEDDING_DIMENSION` | `1024` | Embedding dimension |
| `TFIDF_WEIGHT` | `0.3` | TF-IDF weight (0-1) |
| `EMBEDDING_WEIGHT` | `0.7` | Embedding weight (0-1) |
| `SERVER_PORT` | `9010` | Server port |

## Project Structure

```
faq-mcp-server/
├── faq.py                       # Single-file MCP server
├── regenerate_embeddings.py     # Embedding generation script
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Docker image definition
├── docker-compose.yml           # Docker Compose configuration
├── .env                         # Environment configuration
├── FAQ Data/                    # FAQ source data
│   └── Unified_FAQ.txt
└── README.md                    # Documentation
```

## Usage

### MCP Tool

The server exposes a `search_faq` tool:

```python
search_faq(query: str, top_k: int = 3) -> List[FAQResult]
```

**Example queries:**
- "How do I register for the bootcamp?"
- "Can I use mobile for ViBe?"
- "What are the attendance requirements?"
- "How do I get my certificate?"

### With LibreChat

Configure in `librechat.yaml`:

```yaml
mcpServers:
  faq-server:
    type: streamable-http
    url: http://host.docker.internal:9010/mcp
```

## Regenerating Embeddings

If you update the FAQ data or change the embedding model:

```bash
python regenerate_embeddings.py
```

This will regenerate all embeddings in MongoDB using the configured model.

## Tech Stack

- **Framework**: FastMCP 2.14.2
- **Database**: MongoDB
- **Embeddings**: BAAI/bge-large-en-v1.5 (sentence-transformers)
- **Search**: Hybrid TF-IDF + Semantic
- **Language**: Python 3.12+
---
