FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml ./

# Copy Python modules explicitly
COPY graphiti_memory.py ./
COPY memory_models.py ./
COPY capture.py ./
COPY commands.py ./
COPY mcp_server.py ./
COPY mcp_stdio_wrapper.py ./

# Copy Langfuse integration directory
COPY langfuse_integration/ ./langfuse_integration/

# Copy scripts directory
COPY scripts/ ./scripts/

# Copy documentation
COPY docs/ ./docs/

# Copy test directory
COPY tests/ ./tests/

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Verify critical Python modules can be imported
RUN python -c "import memory_models, capture, graphiti_memory, commands, mcp_server"

# Create directories for Claude commands
RUN mkdir -p /root/.claude/commands

# Set Python unbuffered mode for better logging
ENV PYTHONUNBUFFERED=1

# Default command (can be overridden)
CMD ["python", "mcp_server.py"]