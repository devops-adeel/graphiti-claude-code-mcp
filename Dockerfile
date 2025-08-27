# syntax=docker/dockerfile:1
FROM python:3.11-slim

WORKDIR /app

# NO build-essential needed! All packages have ARM64 wheels

# Copy only requirements first for better caching
COPY pyproject.toml ./

# Use BuildKit cache mount for pip packages
# This caches downloaded wheels between builds
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install \
        graphiti-core>=0.17.9 \
        onepassword-sdk==0.1.3 \
        openai>=1.7.0 \
        python-dotenv>=1.0.0 \
        pydantic>=2.5.0 \
        pydantic-settings>=2.0.0 \
        mcp>=1.0.0 \
        falkordb>=1.0.10 \
        redis>=5.0.0 \
        tiktoken>=0.5.0 \
        langfuse>=2.0.0

# Copy only necessary source files
COPY *.py ./
COPY config/ ./config/
COPY langfuse_integration/ ./langfuse_integration/

# Install package with cache mount
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -e . --no-deps

# Pre-compile Python bytecode for faster startup
RUN python -m compileall -q .

# Verify critical imports still work
RUN python -c "import memory_models, capture, graphiti_memory, commands, secrets_manager"

ENV PYTHONUNBUFFERED=1

CMD ["python", "mcp_server.py"]
