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
COPY *.py ./
COPY tests/ ./tests/

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Create directories for Claude commands
RUN mkdir -p /root/.claude/commands

# Set Python unbuffered mode for better logging
ENV PYTHONUNBUFFERED=1

# Default command (can be overridden)
CMD ["python", "mcp_server.py"]