#!/bin/bash
# Run tests inside Docker/OrbStack for proper networking
# This ensures FalkorDB is accessible via falkordb.local

set -e

echo "========================================="
echo "Running Tests in Docker/OrbStack"
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
TEST_SUITE="all"
PYTEST_ARGS="-v"
KEEP_CONTAINER=false
BUILD_FRESH=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --protocol)
            TEST_SUITE="protocol"
            shift
            ;;
        --integration)
            TEST_SUITE="integration"
            shift
            ;;
        --verbose|-v)
            PYTEST_ARGS="-vv"
            shift
            ;;
        --quiet|-q)
            PYTEST_ARGS="-q"
            shift
            ;;
        --keep)
            KEEP_CONTAINER=true
            shift
            ;;
        --build)
            BUILD_FRESH=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --protocol      Run only MCP protocol tests"
            echo "  --integration   Run only integration tests"
            echo "  --verbose, -v   Show detailed test output"
            echo "  --quiet, -q     Show minimal test output"
            echo "  --keep          Keep container running after tests"
            echo "  --build         Force rebuild of test container"
            echo "  --help, -h      Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                    # Run all tests"
            echo "  $0 --protocol         # Run only protocol tests"
            echo "  $0 --integration -v   # Run integration tests verbosely"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Load environment variables if available
if [ -f "$HOME/.env" ]; then
    export $(grep -v '^#' "$HOME/.env" | xargs)
    echo -e "${GREEN}✓${NC} Loaded environment from ~/.env"
fi

# Check if FalkorDB is accessible
echo -e "\n${BLUE}Checking FalkorDB availability...${NC}"
if docker exec falkordb redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} FalkorDB container is running"
else
    echo -e "${RED}✗${NC} FalkorDB is not accessible"
    echo "  Please ensure FalkorDB is running with OrbStack:"
    echo "  docker run -d --name falkordb -p 6380:6379 --label dev.orbstack.domains=falkordb.local falkordb/falkordb"
    exit 1
fi

# Build test container if needed
if [ "$BUILD_FRESH" = true ] || [ ! "$(docker images -q langfuse-mcp-test 2> /dev/null)" ]; then
    echo -e "\n${BLUE}Building test container...${NC}"
    docker compose -f docker-compose.test.yml build test-runner
    echo -e "${GREEN}✓${NC} Test container built"
fi

# Run tests in Docker
echo -e "\n${BLUE}Running tests in Docker...${NC}"
echo "Test Suite: $TEST_SUITE"
echo "Pytest Args: $PYTEST_ARGS"
echo "========================================="

# Export environment for docker-compose
export TEST_SUITE
export PYTEST_ARGS

# Run the tests
if docker compose -f docker-compose.test.yml run --rm test-runner; then
    TEST_RESULT=0
    echo -e "\n${GREEN}✓ Tests passed successfully${NC}"
else
    TEST_RESULT=$?
    echo -e "\n${RED}✗ Tests failed with exit code $TEST_RESULT${NC}"
fi

# Clean up if not keeping container
if [ "$KEEP_CONTAINER" = false ]; then
    echo -e "\n${BLUE}Cleaning up...${NC}"
    docker compose -f docker-compose.test.yml down 2>/dev/null || true
    echo -e "${GREEN}✓${NC} Cleanup complete"
fi

# Summary
echo ""
echo "========================================="
if [ $TEST_RESULT -eq 0 ]; then
    echo -e "${GREEN}ALL TESTS PASSED${NC}"
    echo ""
    echo "Run specific test suites:"
    echo "  $0 --protocol     # MCP protocol tests only"
    echo "  $0 --integration  # Integration tests only"
    echo ""
    echo "For debugging, keep container running:"
    echo "  $0 --keep"
    echo ""
    echo "Then connect to it:"
    echo "  docker exec -it langfuse-mcp-tests bash"
else
    echo -e "${RED}TESTS FAILED${NC}"
    echo ""
    echo "Debug tips:"
    echo "1. Run with verbose output: $0 -v"
    echo "2. Keep container for inspection: $0 --keep"
    echo "3. Check logs: docker logs langfuse-mcp-tests"
    echo "4. Run specific test:"
    echo "   docker compose -f docker-compose.test.yml run --rm test-runner python -m pytest tests/test_langfuse_e2e.py::TestLangfuseE2EIntegration::test_pattern_signature_generation -v"
fi

exit $TEST_RESULT