# Vision MCP Server
FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (for caching)
RUN pip install --no-cache-dir fastmcp httpx pydantic

# Copy application code
COPY vision_mcp vision_mcp/

# Environment
ENV VISION_API_URL=http://runner:8000
ENV MCP_TRANSPORT=sse
ENV PYTHONPATH=/app

EXPOSE 8080

CMD ["python", "-m", "vision_mcp"]
