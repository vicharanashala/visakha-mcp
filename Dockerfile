# Dockerfile for FAQ MCP Server
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt sentence-transformers

# Copy application files
COPY faq.py .
COPY FAQ_Data ./FAQ_Data

# Expose port
EXPOSE 9010

# Run the server
CMD ["python", "faq.py"]
