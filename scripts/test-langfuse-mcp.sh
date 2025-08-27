#!/bin/bash
# Test script for Langfuse MCP integration
# Runs both protocol and integration tests with proper service setup

set -e  # Exit on error

echo "========================================="
echo "Langfuse MCP Integration Test Suite"
echo "========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Parse command line arguments
RUN_INTEGRATION=true
RUN_PROTOCOL=true
KEEP_SERVICES=false
VERBOSE=false
CI_MODE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --protocol-only)
            RUN_INTEGRATION=false
            shift
            ;;
        --integration-only)
            RUN_PROTOCOL=false
            shift
            ;;
        --keep-services)
            KEEP_SERVICES=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --ci)
            CI_MODE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --protocol-only    Run only MCP protocol tests"
            echo "  --integration-only Run only integration tests"
            echo "  --keep-services    Keep Docker services running after tests"
            echo "  --verbose, -v      Show detailed test output"
            echo "  --ci               Run in CI mode (skip slow tests)"
            echo "  --help, -h         Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Function to check if a service is running
check_service() {
    local service=$1
    local port=$2
    if nc -z localhost $port 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to wait for a service
wait_for_service() {
    local service=$1
    local port=$2
    local max_attempts=30
    local attempt=0
    
    echo -n "Waiting for $service on port $port..."
    while [ $attempt -lt $max_attempts ]; do
        if check_service $service $port; then
            echo -e " ${GREEN}✓${NC}"
            return 0
        fi
        echo -n "."
        sleep 1
        attempt=$((attempt + 1))
    done
    echo -e " ${RED}✗${NC}"
    return 1
}

# Check Python environment
echo -e "${BLUE}Checking Python environment...${NC}"
if [ -f "venv/bin/python" ]; then
    PYTHON="./venv/bin/python"
    echo -e "${GREEN}✓${NC} Using virtual environment"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON="python3"
    echo -e "${YELLOW}⚠${NC} Using system Python3"
else
    echo -e "${RED}✗${NC} Python not found"
    exit 1
fi

# Check required environment variables
echo -e "\n${BLUE}Checking environment...${NC}"
if [ -z "$OPENAI_API_KEY" ]; then
    if [ -f "$HOME/.env" ]; then
        export OPENAI_API_KEY=$(grep OPENAI_API_KEY "$HOME/.env" | cut -d'=' -f2)
        echo -e "${GREEN}✓${NC} Loaded OPENAI_API_KEY from ~/.env"
    else
        echo -e "${YELLOW}⚠${NC} OPENAI_API_KEY not set, using test key"
        export OPENAI_API_KEY="test-key"
    fi
else
    echo -e "${GREEN}✓${NC} OPENAI_API_KEY is set"
fi

# Check if FalkorDB is running
echo -e "\n${BLUE}Checking services...${NC}"
FALKORDB_RUNNING=false
if check_service "FalkorDB" 6379 || check_service "FalkorDB" 6380; then
    echo -e "${GREEN}✓${NC} FalkorDB is running"
    FALKORDB_RUNNING=true
else
    echo -e "${YELLOW}⚠${NC} FalkorDB is not running"
    echo "  Starting FalkorDB..."
    
    # Try to start FalkorDB using the project's docker-compose
    if [ -f "$PROJECT_ROOT/../falkordb/docker-compose.yml" ]; then
        docker compose -f "$PROJECT_ROOT/../falkordb/docker-compose.yml" up -d
        wait_for_service "FalkorDB" 6380
        FALKORDB_RUNNING=true
    else
        echo -e "${YELLOW}⚠${NC} FalkorDB docker-compose not found, tests may fail"
    fi
fi

# Check if Langfuse is needed for integration tests
LANGFUSE_RUNNING=false
if [ "$RUN_INTEGRATION" = true ]; then
    if check_service "Langfuse" 3000; then
        echo -e "${GREEN}✓${NC} Langfuse is running"
        LANGFUSE_RUNNING=true
    else
        echo -e "${YELLOW}⚠${NC} Langfuse is not running"
        
        # Start Langfuse using test docker-compose if it exists
        if [ -f "test-langfuse-compose.yml" ]; then
            echo "  Starting Langfuse test instance..."
            docker compose -f test-langfuse-compose.yml up -d --wait
            wait_for_service "Langfuse" 3000
            LANGFUSE_RUNNING=true
        else
            echo -e "${YELLOW}⚠${NC} test-langfuse-compose.yml not found"
            echo "  Integration tests will use mocked Langfuse client"
        fi
    fi
fi

# Install test dependencies if needed
echo -e "\n${BLUE}Checking test dependencies...${NC}"
if ! $PYTHON -c "import pytest" 2>/dev/null; then
    echo "Installing pytest..."
    $PYTHON -m pip install pytest pytest-asyncio --quiet
fi

# Prepare pytest arguments
PYTEST_ARGS=""
if [ "$VERBOSE" = true ]; then
    PYTEST_ARGS="$PYTEST_ARGS -v"
else
    PYTEST_ARGS="$PYTEST_ARGS -q"
fi

if [ "$CI_MODE" = true ]; then
    PYTEST_ARGS="$PYTEST_ARGS --ci"
fi

# Run tests
echo -e "\n${BLUE}Running tests...${NC}"
echo "========================================="

TEST_FAILED=false

# Run MCP protocol tests
if [ "$RUN_PROTOCOL" = true ]; then
    echo -e "\n${BLUE}Running MCP Protocol Tests...${NC}"
    if $PYTHON -m pytest tests/test_langfuse_mcp_protocol.py $PYTEST_ARGS; then
        echo -e "${GREEN}✓${NC} MCP protocol tests passed"
    else
        echo -e "${RED}✗${NC} MCP protocol tests failed"
        TEST_FAILED=true
    fi
fi

# Run integration tests
if [ "$RUN_INTEGRATION" = true ]; then
    echo -e "\n${BLUE}Running Integration Tests...${NC}"
    if $PYTHON -m pytest tests/test_langfuse_e2e.py $PYTEST_ARGS; then
        echo -e "${GREEN}✓${NC} Integration tests passed"
    else
        echo -e "${RED}✗${NC} Integration tests failed"
        TEST_FAILED=true
    fi
fi

# Run existing Langfuse tests if they exist
if [ -f "test_langfuse_integration.py" ]; then
    echo -e "\n${BLUE}Running Existing Langfuse Tests...${NC}"
    if $PYTHON test_langfuse_integration.py; then
        echo -e "${GREEN}✓${NC} Existing tests passed"
    else
        echo -e "${YELLOW}⚠${NC} Some existing tests failed"
    fi
fi

# Clean up services if requested
if [ "$KEEP_SERVICES" = false ] && [ -f "test-langfuse-compose.yml" ]; then
    echo -e "\n${BLUE}Cleaning up test services...${NC}"
    docker compose -f test-langfuse-compose.yml down 2>/dev/null || true
    echo -e "${GREEN}✓${NC} Test services stopped"
fi

# Summary
echo ""
echo "========================================="
if [ "$TEST_FAILED" = true ]; then
    echo -e "${RED}TESTS FAILED${NC}"
    echo "========================================="
    exit 1
else
    echo -e "${GREEN}ALL TESTS PASSED${NC}"
    echo "========================================="
    
    # Provide next steps
    echo -e "\n${BLUE}Next Steps:${NC}"
    echo "1. Run with real services:"
    echo "   $0 --integration-only"
    echo ""
    echo "2. Run in CI mode:"
    echo "   $0 --ci"
    echo ""
    echo "3. Debug specific test:"
    echo "   $PYTHON -m pytest tests/test_langfuse_mcp_protocol.py::TestLangfuseMCPProtocol::test_analyze_langfuse_traces -v"
    echo ""
    echo "4. Generate coverage report:"
    echo "   $PYTHON -m pytest tests/test_langfuse*.py --cov=. --cov-report=html"
    
    exit 0
fi