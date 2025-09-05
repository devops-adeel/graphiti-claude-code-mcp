# syntax=docker/dockerfile:1
FROM python:3.11-slim

WORKDIR /app

# Install ca-certificates for SSL verification and wget for downloads
RUN apt-get update && apt-get install -y ca-certificates wget && rm -rf /var/lib/apt/lists/*

# Copy only requirements first for better caching
COPY pyproject.toml ./

# Use BuildKit cache mount for pip packages
# This caches downloaded wheels between builds
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install \
        "graphiti-core[neo4j]>=0.18.9,<0.19.0" \
        onepassword-sdk==0.1.3 \
        openai>=1.7.0 \
        python-dotenv>=1.0.0 \
        pydantic>=2.5.0 \
        pydantic-settings>=2.0.0 \
        mcp>=1.0.0 \
        neo4j>=5.0.0 \
        tiktoken>=0.5.0 \
        langfuse>=3.3.0 \
        ollama>=0.1.0

# Copy only necessary source files
COPY *.py ./
# Explicitly copy Ollama integration files
COPY ollama_native_client.py ./
COPY ollama_embedder_wrapper.py ./
COPY config/ ./config/
COPY langfuse_integration/ ./langfuse_integration/
COPY instrumentation/ ./instrumentation/

# Install package with cache mount
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -e . --no-deps

# Neo4j support is native in graphiti-core - no patches needed

# Pre-compile Python bytecode for faster startup
RUN python -m compileall -q .

# Pre-download tiktoken encodings with proper SSL for offline use
ENV TIKTOKEN_CACHE_DIR=/app/.tiktoken_cache
RUN mkdir -p $TIKTOKEN_CACHE_DIR && \
    wget -q https://openaipublic.blob.core.windows.net/encodings/o200k_base.tiktoken \
         -O $TIKTOKEN_CACHE_DIR/fb374d419588a4632f3f557e76b4b70aebbca790 && \
    wget -q https://openaipublic.blob.core.windows.net/encodings/cl100k_base.tiktoken \
         -O $TIKTOKEN_CACHE_DIR/9b5ad71b2ce5302211f9c61530b329a4922fc6a4

# Verify critical imports still work
RUN python -c "import memory_models, capture, graphiti_memory, commands, secrets_manager"

ENV PYTHONUNBUFFERED=1

# Create entrypoint to handle OrbStack certificate if present
RUN echo '#!/bin/sh' > /docker-entrypoint.sh && \
    echo '# Ensure tiktoken cache directory is set' >> /docker-entrypoint.sh && \
    echo 'export TIKTOKEN_CACHE_DIR=/app/.tiktoken_cache' >> /docker-entrypoint.sh && \
    echo '# Disable SSL verification for requests (tiktoken workaround)' >> /docker-entrypoint.sh && \
    echo 'export CURL_CA_BUNDLE=""' >> /docker-entrypoint.sh && \
    echo 'export REQUESTS_CA_BUNDLE=""' >> /docker-entrypoint.sh && \
    echo 'export PYTHONWARNINGS="ignore:Unverified HTTPS request"' >> /docker-entrypoint.sh && \
    echo '# OrbStack cert is already mounted at correct location' >> /docker-entrypoint.sh && \
    echo '# Just update certificates if the OrbStack cert exists' >> /docker-entrypoint.sh && \
    echo 'if [ -f "/usr/local/share/ca-certificates/orbstack-root.crt" ]; then' >> /docker-entrypoint.sh && \
    echo '    update-ca-certificates > /dev/null 2>&1' >> /docker-entrypoint.sh && \
    echo 'fi' >> /docker-entrypoint.sh && \
    echo 'exec python mcp_server.py' >> /docker-entrypoint.sh && \
    chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
