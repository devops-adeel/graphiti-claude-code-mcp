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
	@echo "  2. $(GREEN)make up-secure$(NC)        - Start with 1Password (zero Touch ID)"
	@echo "  3. $(GREEN)make logs$(NC)             - View logs"

# === Configuration Management ===

.PHONY: fix-config
fix-config: ## Fix configuration to match GTD Coach
	@echo "$(BLUE)Fixing configuration alignment with GTD Coach...$(NC)"
	@cp .env.graphiti .env.graphiti.backup 2>/dev/null || true
	@sed -i '' 's/GRAPHITI_GROUP_ID=shared_gtd_knowledge/GRAPHITI_GROUP_ID=shared_knowledge/g' .env.graphiti
	@sed -i '' 's/FALKORDB_DATABASE=shared_knowledge_graph/FALKORDB_DATABASE=shared_gtd_knowledge/g' .env.graphiti
	@echo "$(GREEN)✅ Configuration fixed$(NC)"
	@echo "  GRAPHITI_GROUP_ID: shared_knowledge"
	@echo "  FALKORDB_DATABASE: shared_gtd_knowledge"

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
	@if grep -q "FALKORDB_DATABASE=shared_gtd_knowledge" .env.graphiti; then \
		echo "$(GREEN)✅ FALKORDB_DATABASE correct$(NC)"; \
	else \
		echo "$(RED)❌ FALKORDB_DATABASE incorrect$(NC)"; \
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
build: ## Build Docker image
	@echo "$(BLUE)Building Docker image...$(NC)"
	@docker compose build --no-cache
	@echo "$(GREEN)✅ Image built: $(DOCKER_IMAGE)$(NC)"

.PHONY: up
up: verify-config ## Start with .env.graphiti (standard mode)
	@echo "$(BLUE)Starting with standard configuration...$(NC)"
	@./scripts/start-standard.sh

.PHONY: up-secure
up-secure: verify-config ## Start with 1Password (zero Touch ID)
	@echo "$(BLUE)Starting with 1Password secrets...$(NC)"
	@./scripts/start-with-1password.sh

.PHONY: down
down: ## Stop all services
	@echo "$(BLUE)Stopping services...$(NC)"
	@docker compose down
	@echo "$(GREEN)✅ Services stopped$(NC)"

.PHONY: restart
restart: down up ## Restart services

.PHONY: restart-secure
restart-secure: down up-secure ## Restart with 1Password

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
test-connection: ## Test FalkorDB connection
	@echo "$(BLUE)Testing FalkorDB connection...$(NC)"
	@docker compose run --rm test-runner "redis-cli -h falkordb -p 6379 ping" && \
		echo "$(GREEN)✅ FalkorDB is accessible$(NC)" || \
		echo "$(RED)❌ Cannot connect to FalkorDB$(NC)"

.PHONY: test-health-1p
test-health-1p: ## Run health check with 1Password secrets
	@echo "$(BLUE)Running health check with 1Password...$(NC)"
	@source $(SERVICE_TOKEN_FILE) && \
	op run --env-file="secrets/.env.1password" -- \
	docker compose run --rm \
	-e FALKORDB_HOST=falkordb \
	graphiti-mcp python scripts/health_check_memory.py

.PHONY: test-mcp-1p
test-mcp-1p: ## Test MCP server with 1Password
	@echo "$(BLUE)Testing MCP server with 1Password...$(NC)"
	@source $(SERVICE_TOKEN_FILE) && \
	op run --env-file="secrets/.env.1password" -- \
	docker compose run --rm \
	-e FALKORDB_HOST=falkordb \
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

# === Information ===

.PHONY: info
info: ## Show current configuration
	@echo "$(BLUE)Current Configuration:$(NC)"
	@echo ""
	@echo "Knowledge Sharing:"
	@grep "GRAPHITI_GROUP_ID\|FALKORDB_DATABASE" .env.graphiti | sed 's/^/  /'
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

# === Development ===

.PHONY: shell
shell: ## Open shell in running container
	@docker exec -it graphiti-claude-code-mcp /bin/bash

.PHONY: python
python: ## Open Python REPL in container
	@docker exec -it graphiti-claude-code-mcp python

.PHONY: rebuild
rebuild: down build up ## Rebuild and restart

.PHONY: rebuild-secure
rebuild-secure: down build up-secure ## Rebuild and restart with 1Password