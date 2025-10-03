FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including Node.js and git for Planka MCP integration
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    git \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Clone and build kanban-mcp for Planka integration
# Using lwgray fork with project/board creation features
RUN git clone --branch feature/add-project-crud-operations https://github.com/lwgray/kanban-mcp.git /app/kanban-mcp && \
    cd /app/kanban-mcp && \
    npm install && \
    npm run build

# Copy application code
COPY . .

# Set Python path
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Create necessary directories
RUN mkdir -p logs data logs/conversations

# Create default config file if it doesn't exist
# This ensures the container can start even without mounted config
RUN if [ ! -f config_marcus.json ] && [ -f config_marcus.example.json ]; then \
    cp config_marcus.example.json config_marcus.json; \
    fi

# Expose MCP stdio interface (not a network port)
# MCP uses stdio, not HTTP

# Default command - run Marcus MCP server
CMD ["python", "-m", "src.marcus_mcp.server"]
