# Makefile for Graphiti MCP Server
# Provides easy management of 1Password integration and Docker services

# Variables
SERVICE_TOKEN_FILE := $(HOME)/.config/graphiti-mcp/service-token
DOCKER_IMAGE := graphiti-mcp-server:latest
PROJECT_NAME := graphiti-claude-code-mcp

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

# Default target
.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help message
	@echo "$(BLUE)Graphiti MCP Server Management$(NC)"
	@echo ""
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "Quick start:"
	@echo "  1. $(GREEN)make setup-1password$(NC)  - One-time 1Password setup"
	@echo "  2. $(GREEN)make up$(NC)               - Start with 1Password"
	@echo "  3. $(GREEN)make logs$(NC)             - View logs"

# === Configuration Management ===

.PHONY: fix-config
fix-config: ## Fix configuration to match GTD Coach
	@echo "$(BLUE)Fixing configuration alignment with GTD Coach...$(NC)"
	@cp .env.graphiti .env.graphiti.backup 2>/dev/null || true
	@sed -i '' 's/GRAPHITI_GROUP_ID=shared_gtd_knowledge/GRAPHITI_GROUP_ID=shared_knowledge/g' .env.graphiti
	@sed -i '' 's/NEO4J_DATABASE=shared_knowledge_graph/NEO4J_DATABASE=neo4j/g' .env.graphiti
	@sed -i '' 's/NEO4J_DATABASE=shared_gtd_knowledge/NEO4J_DATABASE=neo4j/g' .env.graphiti
	@echo "$(GREEN)✅ Configuration fixed$(NC)"
	@echo "  GRAPHITI_GROUP_ID: shared_knowledge"
	@echo "  NEO4J_DATABASE: neo4j (Community Edition requirement)"

.PHONY: verify-config
verify-config: ## Verify configuration matches GTD Coach
	@echo "$(BLUE)Verifying configuration alignment...$(NC)"
	@if grep -q "GRAPHITI_GROUP_ID=shared_knowledge" .env.graphiti; then \
		echo "$(GREEN)✅ GRAPHITI_GROUP_ID correct$(NC)"; \
	else \
		echo "$(RED)❌ GRAPHITI_GROUP_ID incorrect$(NC)"; \
		echo "  Run: make fix-config"; \
		exit 1; \
	fi
	@if grep -q "NEO4J_DATABASE=neo4j" .env.graphiti; then \
		echo "$(GREEN)✅ NEO4J_DATABASE correct (neo4j for Community Edition)$(NC)"; \
	else \
		echo "$(RED)❌ NEO4J_DATABASE incorrect (must be 'neo4j' for Community Edition)$(NC)"; \
		echo "  Run: make fix-config"; \
		exit 1; \
	fi

# === 1Password Setup ===

.PHONY: setup-1password
setup-1password: ## Complete 1Password setup (requires admin)
	@echo "$(BLUE)Setting up 1Password integration...$(NC)"
	@./scripts/setup-1password.sh

.PHONY: test-1password
test-1password: ## Test 1Password configuration
	@echo "$(BLUE)Testing 1Password configuration...$(NC)"
	@if [ -f $(SERVICE_TOKEN_FILE) ]; then \
		. $(SERVICE_TOKEN_FILE) && \
		if op inject -i secrets/.env.1password >/dev/null 2>&1; then \
			echo "$(GREEN)✅ 1Password configured correctly$(NC)"; \
			echo "  Service Account token: Active"; \
			echo "  Secrets accessible: Yes"; \
			echo "  Touch ID required: No"; \
		else \
			echo "$(RED)❌ 1Password secrets not accessible$(NC)"; \
			echo "  Check Service Account token"; \
			exit 1; \
		fi; \
	else \
		echo "$(YELLOW)⚠️  Service Account token not found$(NC)"; \
		echo "  Location: $(SERVICE_TOKEN_FILE)"; \
		echo "  Run: make setup-1password"; \
		exit 1; \
	fi

.PHONY: show-secrets
show-secrets: ## Show secret references (not actual secrets)
	@echo "$(BLUE)Secret references in use:$(NC)"
	@cat secrets/.env.1password | grep "^[A-Z]" | sed 's/=op:\/\/.*/=<1Password Reference>/'

# === Docker Service Management ===

.PHONY: build
build: ## Build Docker image with 1Password secrets
	@echo "$(BLUE)Building Docker image with 1Password context...$(NC)"
	@if [ -f $(SERVICE_TOKEN_FILE) ]; then \
		source $(SERVICE_TOKEN_FILE) && \
		op run --env-file=secrets/.env.1password -- docker compose build --no-cache; \
	else \
		echo "$(YELLOW)⚠️  Building without 1Password (secrets not available during build)$(NC)"; \
		docker compose build --no-cache; \
	fi
	@# Tag the image with the expected name for the wrapper script
	@docker tag graphiti-claude-code-mcp-graphiti-mcp:latest $(DOCKER_IMAGE) 2>/dev/null || true
	@echo "$(GREEN)✅ Image built: $(DOCKER_IMAGE)$(NC)"

.PHONY: up
up: verify-config ## Start with 1Password secrets
	@echo "$(BLUE)Starting with 1Password secrets...$(NC)"
	@./scripts/start-with-1password.sh

.PHONY: down
down: ## Stop all services
	@echo "$(BLUE)Stopping services...$(NC)"
	@docker compose down
	@echo "$(GREEN)✅ Services stopped$(NC)"

.PHONY: restart
restart: down up ## Restart services with 1Password

.PHONY: logs
logs: ## View logs (follow mode)
	@docker compose logs -f

.PHONY: logs-tail
logs-tail: ## View last 50 lines of logs
	@docker compose logs --tail=50

.PHONY: ps
ps: ## Show running services
	@docker compose ps

# === Memory Pipeline Health Check ===

.PHONY: health-check
health-check: ## Run memory pipeline health check
	@echo "$(BLUE)Running memory pipeline health check...$(NC)"
	@python3 scripts/health_check_memory.py

.PHONY: health-check-verbose
health-check-verbose: ## Run detailed health check with queries
	@echo "$(BLUE)Running detailed health check...$(NC)"
	@python3 scripts/health_check_memory.py --verbose

.PHONY: health-check-fix
health-check-fix: ## Run health check with fix suggestions
	@echo "$(BLUE)Running health check with fix suggestions...$(NC)"
	@python3 scripts/health_check_memory.py --fix

.PHONY: health-check-all
health-check-all: ## Run comprehensive health check (verbose + fix)
	@echo "$(BLUE)Running comprehensive health check...$(NC)"
	@python3 scripts/health_check_memory.py --verbose --fix

# === Testing & Verification ===

.PHONY: test-connection
test-connection: ## Test Neo4j connection
	@echo "$(BLUE)Testing Neo4j connection...$(NC)"
	@docker compose run --rm test-runner "nc -z neo4j.graphiti.local 7687" && \
		echo "$(GREEN)✅ Neo4j is accessible$(NC)" || \
		echo "$(RED)❌ Cannot connect to Neo4j$(NC)"

# === Behavioral Correlation Testing ===

.PHONY: test-behavioral
test-behavioral: ## Run behavioral correlation tests in Docker
	@echo "$(BLUE)Running behavioral correlation tests...$(NC)"
	@docker compose -f docker-compose.yml -f docker-compose.test.yml up test-behavioral --abort-on-container-exit
	@echo "$(GREEN)✅ Behavioral tests completed$(NC)"
	@echo "Results saved to test-results/"

.PHONY: test-unit
test-unit: ## Run unit tests (no Neo4j required)
	@echo "$(BLUE)Running unit tests...$(NC)"
	@python3 -m pytest tests/test_implicit_scoring_unit.py -v --tb=short
	@echo "$(GREEN)✅ Unit tests completed$(NC)"

.PHONY: test-integration
test-integration: ## Run integration tests with Neo4j
	@echo "$(BLUE)Starting Neo4j test instance...$(NC)"
	@docker compose -f docker-compose.test.yml up -d neo4j-test
	@echo "$(BLUE)Waiting for Neo4j to be ready...$(NC)"
	@sleep 10
	@echo "$(BLUE)Running integration tests...$(NC)"
	@NEO4J_URI=bolt://localhost:7688 python3 -m pytest tests/test_implicit_scoring_integration.py -v --tb=short -m integration
	@docker compose -f docker-compose.test.yml down neo4j-test
	@echo "$(GREEN)✅ Integration tests completed$(NC)"

.PHONY: test-docker
test-docker: ## Run all tests in Docker environment
	@echo "$(BLUE)Running all tests in Docker...$(NC)"
	@docker compose -f docker-compose.yml -f docker-compose.test.yml up --abort-on-container-exit
	@echo "$(GREEN)✅ All Docker tests completed$(NC)"

.PHONY: test-coverage
test-coverage: ## Generate test coverage report
	@echo "$(BLUE)Generating test coverage report...$(NC)"
	@python3 -m pytest tests/test_implicit_scoring_unit.py \
		--cov=capture_extended --cov-report=html:test-results/coverage \
		--cov-report=term
	@echo "$(GREEN)✅ Coverage report generated in test-results/coverage$(NC)"

.PHONY: test-clean
test-clean: ## Clean test artifacts
	@echo "$(BLUE)Cleaning test artifacts...$(NC)"
	@rm -rf test-results/
	@docker compose -f docker-compose.test.yml down -v
	@echo "$(GREEN)✅ Test cleanup complete$(NC)"

.PHONY: test
test: test-unit test-integration ## Run all tests locally

.PHONY: test-health-1p
test-health-1p: ## Run health check with 1Password secrets
	@echo "$(BLUE)Running health check with 1Password...$(NC)"
	@source $(SERVICE_TOKEN_FILE) && \
	op run --env-file="secrets/.env.1password" -- \
	docker compose run --rm \
	-e NEO4J_URI=bolt://neo4j.graphiti.local:7687 \
	graphiti-mcp python scripts/health_check_memory.py

.PHONY: test-mcp-1p
test-mcp-1p: ## Test MCP server with 1Password
	@echo "$(BLUE)Testing MCP server with 1Password...$(NC)"
	@source $(SERVICE_TOKEN_FILE) && \
	op run --env-file="secrets/.env.1password" -- \
	docker compose run --rm \
	-e NEO4J_URI=bolt://neo4j.graphiti.local:7687 \
	graphiti-mcp python mcp_server.py

.PHONY: test-sharing
test-sharing: ## Test knowledge sharing setup
	@echo "$(BLUE)Testing knowledge sharing configuration...$(NC)"
	@docker exec graphiti-claude-code-mcp python -c "\
		from graphiti_memory import get_shared_memory; \
		import asyncio; \
		async def test(): \
			mem = await get_shared_memory(); \
			print(f'Database: {mem.database}'); \
			print(f'Group ID: {mem.group_id}'); \
		asyncio.run(test())" 2>/dev/null || echo "$(YELLOW)Container not running$(NC)"

.PHONY: test-all
test-all: test-1password test-connection test-sharing ## Run all tests

# === Cleanup ===

.PHONY: clean
clean: ## Clean up temporary files
	@echo "$(BLUE)Cleaning up...$(NC)"
	@rm -f .env.graphiti.backup
	@docker compose down -v 2>/dev/null || true
	@echo "$(GREEN)✅ Cleanup complete$(NC)"

.PHONY: clean-all
clean-all: clean ## Clean everything including Service Account token
	@echo "$(YELLOW)⚠️  Removing Service Account token...$(NC)"
	@rm -f $(SERVICE_TOKEN_FILE)
	@echo "$(GREEN)✅ All configurations removed$(NC)"

.PHONY: clean-images
clean-images: ## Remove old Docker images
	@echo "$(BLUE)Cleaning up old Docker images...$(NC)"
	@# Remove all graphiti-mcp images except the latest graphiti-mcp-server
	@docker images | grep graphiti | grep -v "graphiti-mcp-server.*latest" | awk '{print $$3}' | xargs -r docker rmi -f 2>/dev/null || true
	@echo "$(GREEN)✅ Old images cleaned$(NC)"

# === Information ===

.PHONY: info
info: ## Show current configuration
	@echo "$(BLUE)Current Configuration:$(NC)"
	@echo ""
	@echo "Knowledge Sharing:"
	@grep "GRAPHITI_GROUP_ID\|NEO4J_DATABASE" .env.graphiti | sed 's/^/  /'
	@echo ""
	@echo "1Password Status:"
	@if [ -f $(SERVICE_TOKEN_FILE) ]; then \
		echo "  $(GREEN)✓$(NC) Service Account configured"; \
	else \
		echo "  $(YELLOW)✗$(NC) Service Account not configured"; \
	fi
	@echo ""
	@echo "Docker Status:"
	@docker compose ps --format "table {{.Service}}\t{{.Status}}" 2>/dev/null || echo "  No services running"

.PHONY: version
version: ## Show versions
	@echo "$(BLUE)Version Information:$(NC)"
	@echo "  Docker: $$(docker --version)"
	@echo "  Docker Compose: $$(docker compose version)"
	@echo "  1Password CLI: $$(op --version 2>/dev/null || echo 'Not installed')"
	@echo "  Project: $(PROJECT_NAME)"

# === Claude Code Integration ===

.PHONY: claude-setup
claude-setup: build verify-config test-1password ## Complete setup for Claude Code
	@echo "$(BLUE)Setting up for Claude Code...$(NC)"
	@./scripts/verify-mcp-ready.sh
	@echo ""
	@echo "$(GREEN)Next steps:$(NC)"
	@echo "1. Run the command shown above to add the MCP server"
	@echo "2. Restart Claude Code"
	@echo "3. Test with: 'Search your memory for recent patterns'"

.PHONY: claude-test
claude-test: ## Test MCP server readiness for Claude Code
	@./scripts/verify-mcp-ready.sh

# === Development ===

.PHONY: shell
shell: ## Open shell in running container
	@docker exec -it graphiti-claude-code-mcp /bin/bash

.PHONY: python
python: ## Open Python REPL in container
	@docker exec -it graphiti-claude-code-mcp python

.PHONY: rebuild
rebuild: down build up ## Rebuild and restart with 1Password

# === SSL & Langfuse Diagnostics ===

.PHONY: ssl-check
ssl-check: ## Check SSL configuration
	@echo "$(BLUE)Checking SSL configuration...$(NC)"
	@python ssl_config.py http://langfuse.local || true
	@echo ""
	@echo "$(BLUE)SSL Config Details:$(NC)"
	@python -c "from ssl_config import get_ssl_config; c=get_ssl_config(); import json; print(json.dumps(c.get_info(), indent=2))"

.PHONY: langfuse-health
langfuse-health: ## Run Langfuse connection health check
	@echo "$(BLUE)Running Langfuse health check...$(NC)"
	@python scripts/health_check_langfuse.py

.PHONY: langfuse-health-verbose
langfuse-health-verbose: ## Run verbose Langfuse health check with debugging
	@echo "$(BLUE)Running verbose Langfuse health check...$(NC)"
	@python scripts/health_check_langfuse.py --verbose

.PHONY: test-langfuse-local
test-langfuse-local: ## Test Langfuse connection locally
	@echo "$(BLUE)Testing Langfuse connection locally...$(NC)"
	@export LANGFUSE_HOST=http://langfuse.local && \
	export LANGFUSE_PUBLIC_KEY=$$(op item get ctyxybforywkjp2krbdpeulzzq --fields "Langfuse.langfuse-public-key" 2>/dev/null) && \
	export LANGFUSE_SECRET_KEY=$$(op item get ctyxybforywkjp2krbdpeulzzq --fields "Langfuse.langfuse-secret-key" 2>/dev/null) && \
	python -c "from ssl_config import create_langfuse_httpx_client; from langfuse import Langfuse; import os; \
	client = Langfuse(public_key=os.getenv('LANGFUSE_PUBLIC_KEY'), secret_key=os.getenv('LANGFUSE_SECRET_KEY'), \
	host=os.getenv('LANGFUSE_HOST'), httpx_client=create_langfuse_httpx_client()); \
	result = client.api.trace.list(limit=1); \
	print('✅ Connected successfully!'); \
	print(f'Found {len(result.data)} traces')"

.PHONY: test-langfuse-docker
test-langfuse-docker: ## Test Langfuse connection from Docker container
	@echo "$(BLUE)Testing Langfuse connection from Docker...$(NC)"
	@docker run --rm \
		--network orbstack-shared \
		-e LANGFUSE_HOST=http://langfuse-web:3000 \
		-e LANGFUSE_PUBLIC_KEY=$$(op item get ctyxybforywkjp2krbdpeulzzq --fields "Langfuse.langfuse-public-key" 2>/dev/null) \
		-e LANGFUSE_SECRET_KEY=$$(op item get ctyxybforywkjp2krbdpeulzzq --fields "Langfuse.langfuse-secret-key" 2>/dev/null) \
		-v $(PWD):/app \
		-w /app \
		$(DOCKER_IMAGE) \
		python scripts/health_check_langfuse.py

.PHONY: fix-ssl
fix-ssl: ## Apply SSL certificate fixes
	@echo "$(BLUE)Applying SSL certificate fixes...$(NC)"
	@echo "$(YELLOW)1. Checking for OrbStack certificate...$(NC)"
	@if [ -f /usr/local/share/ca-certificates/orbstack-root.crt ]; then \
		echo "$(GREEN)✅ OrbStack certificate found$(NC)"; \
		export SSL_CERT_FILE=/usr/local/share/ca-certificates/orbstack-root.crt; \
		echo "$(GREEN)✅ Set SSL_CERT_FILE=$(NC)"; \
	else \
		echo "$(YELLOW)⚠️  OrbStack certificate not found$(NC)"; \
	fi
	@echo ""
	@echo "$(YELLOW)2. Setting Langfuse environment...$(NC)"
	@echo "export LANGFUSE_HOST=http://langfuse.local"
	@echo "export SSL_CERT_FILE=/usr/local/share/ca-certificates/orbstack-root.crt"
	@echo ""
	@echo "$(GREEN)Run these commands in your shell:$(NC)"
	@echo "  export LANGFUSE_HOST=http://langfuse.local"
	@echo "  export SSL_CERT_FILE=/usr/local/share/ca-certificates/orbstack-root.crt"
