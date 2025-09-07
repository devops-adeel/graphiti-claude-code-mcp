# Changelog

All notable changes to Graphiti Claude Code MCP will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
## [5.0.1](https://github.com/adeel/graphiti-claude-code-mcp/compare/v5.0.0..v5.0.1) - 2025-09-07


### 🐛 Bug Fixes

- Resolve Ollama SSL/TLS connection issues
## [5.0.0](https://github.com/adeel/graphiti-claude-code-mcp/compare/v4.0.0..v5.0.0) - 2025-09-07


### 🚀 Features

- *(cascade)* Add Gen AI behavioral pattern detection

### 🚜 Refactor

- [**breaking**] Remove os.getenv defaults to enforce explicit configuration
## [4.0.0](https://github.com/adeel/graphiti-claude-code-mcp/compare/v3.4.1..v4.0.0) - 2025-09-05


### 🚀 Features

- *(observability)* Add dual export to Alloy and Langfuse OTLP

### 🐛 Bug Fixes

- *(mcp)* Adjust server initialization for Ollama client

### 🚜 Refactor

- *(llm)* [**breaking**] Migrate from hybrid OpenAI/Ollama to pure Ollama

### 📚 Documentation

- Add 1024-dimension solution documentation

### ⚙️ Miscellaneous Tasks

- *(build)* Update Docker and Make configurations
## [3.4.1](https://github.com/adeel/graphiti-claude-code-mcp/compare/v3.4.0..v3.4.1) - 2025-09-04


### 🐛 Bug Fixes

- *(langfuse)* Switch from HTTPS to HTTP for local development

### 📚 Documentation

- *(changelog)* Update for v3.4.1 release

### ⚙️ Miscellaneous Tasks

- *(release)* Bump version to 3.4.1
## [3.4.0](https://github.com/adeel/graphiti-claude-code-mcp/compare/v3.3.1..v3.4.0) - 2025-09-04


### 🚀 Features

- *(ollama)* Implement native client with structured output

### 🐛 Bug Fixes

- *(embedder)* Resolve parameter mismatch for Ollama integration

### 🚜 Refactor

- *(memory)* Integrate native Ollama client and embedder

### 📚 Documentation

- *(ollama)* Comprehensive solution documentation

### 🧪 Testing

- *(ollama)* Add comprehensive validation suite

### ⚙️ Miscellaneous Tasks

- *(config)* Update build and test configuration
## [3.3.1](https://github.com/adeel/graphiti-claude-code-mcp/compare/v3.2.1..v3.3.1) - 2025-09-03


### 🚀 Features

- Add 'The AI That Never Forgets' conceptual video documentation

### 🐛 Bug Fixes

- Sync pyproject.toml version with CHANGELOG
- *(otlp)* Use HTTP endpoint to bypass SSL verification issues

### 🚜 Refactor

- Migrate to Langfuse SDK v3 with OrbStack SSL support

### 📚 Documentation

- Document Langfuse storage failure investigation and solution
- Update CHANGELOG for OTLP HTTP fix

### 🧪 Testing

- Migrate loop prevention tests to Langfuse SDK v3

### ⚙️ Miscellaneous Tasks

- Add root-level test files to .gitignore
## [3.2.1](https://github.com/adeel/graphiti-claude-code-mcp/compare/v3.2.0..v3.2.1) - 2025-09-02


### 🐛 Bug Fixes

- *(auth)* Implement lazy Langfuse initialization with proper secret injection

### 🚜 Refactor

- *(config)* Standardize group_id to 'shared_knowledge' across system
## [3.2.0](https://github.com/adeel/graphiti-claude-code-mcp/compare/v3.1.1..v3.2.0) - 2025-09-02


### 🚀 Features

- [**breaking**] Make Langfuse integration mandatory for observability
- *(scoring)* Implement Langfuse-first behavioral scoring system
- *(observability)* Add W3C Trace Context correlation

### 💼 Other

- Update Makefile with behavioral testing targets

### 🧪 Testing

- Add comprehensive behavioral validation suite
## [3.1.1](https://github.com/adeel/graphiti-claude-code-mcp/compare/v3.1.0..v3.1.1) - 2025-09-01


### 🐛 Bug Fixes

- *(docker)* Resolve tiktoken SSL certificate errors

### 🚜 Refactor

- Remove obsolete FalkorDB patches and tests
- *(test)* Consolidate test configurations

### ⚙️ Miscellaneous Tasks

- Update configuration and documentation
- Update tests and gitleaks configuration
## [3.1.0](https://github.com/adeel/graphiti-claude-code-mcp/compare/v3.0.0..v3.1.0) - 2025-09-01


### 🚀 Features

- *(observability)* Add OpenTelemetry instrumentation

### 📚 Documentation

- Update changelog for v3.0.0 migration

### ⚙️ Miscellaneous Tasks

- Complete Neo4j migration cleanup
- *(docker)* Consolidate Docker networks to orbstack-shared
## [3.0.0](https://github.com/adeel/graphiti-claude-code-mcp/compare/v2.1.0..v3.0.0) - 2025-08-31


### 🚀 Features

- [**breaking**] Migrate from FalkorDB to Neo4j backend
## [2.1.0](https://github.com/adeel/graphiti-claude-code-mcp/compare/v2.0.3..v2.1.0) - 2025-08-30


### 🚀 Features

- *(config)* Add GRAPHITI_BATCH_SIZE environment variable

### 🐛 Bug Fixes

- *(memory)* Force immediate persistence to prevent data loss

### 🧪 Testing

- *(memory)* Add diagnostic tool for persistence verification
## [2.0.3](https://github.com/adeel/graphiti-claude-code-mcp/compare/v2.0.2..v2.0.3) - 2025-08-29


### 🐛 Bug Fixes

- *(1password)* Resolve rate limiting and improve resilience
## [2.0.2](https://github.com/adeel/graphiti-claude-code-mcp/compare/v2.0.1..v2.0.2) - 2025-08-29


### 🐛 Bug Fixes

- *(falkordb)* [**breaking**] Add compatibility patches for Graphiti v0.18.9
## [2.0.1](https://github.com/adeel/graphiti-claude-code-mcp/compare/v2.0.0..v2.0.1) - 2025-08-28


### 🐛 Bug Fixes

- *(docker)* Migrate to orbstack-shared network configuration
## [2.0.0](https://github.com/adeel/graphiti-claude-code-mcp/compare/v1.1.0..v2.0.0) - 2025-08-28


### 🚀 Features

- *(memory)* Add session summary capture

### 🚜 Refactor

- *(docs)* [**breaking**] Implement Diátaxis framework

### ⚙️ Miscellaneous Tasks

- *(release)* [**breaking**] V2.0.0
## [1.1.0](https://github.com/adeel/graphiti-claude-code-mcp/compare/v1.0.2..v1.1.0) - 2025-08-28


### 🚀 Features

- *(security)* Enhance pre-commit hooks and dependency management
- *(config)* Add multi-environment support with SSL
- *(monitoring)* Add comprehensive health checks

### 📚 Documentation

- Add setup guides and security documentation

### ⚙️ Miscellaneous Tasks

- Update cliff configuration with repository URL
## [1.0.2](https://github.com/adeel/graphiti-claude-code-mcp/compare/v1.0.1..v1.0.2) - 2025-08-28


### 🚜 Refactor

- *(config)* Simplify shared knowledge database names

### ⚙️ Miscellaneous Tasks

- *(release)* Update CHANGELOG.md for v1.0.2
## [1.0.1](https://github.com/adeel/graphiti-claude-code-mcp/compare/v1.0.0..v1.0.1) - 2025-08-28


### 🐛 Bug Fixes

- *(network)* Enable flexible Docker networking configuration

### ⚙️ Miscellaneous Tasks

- *(release)* Update CHANGELOG.md for v1.0.1
## [1.0.0](https://github.com/adeel/graphiti-claude-code-mcp/compare/v0.3.0..v1.0.0) - 2025-08-28


### 🚀 Features

- *(security)* Add 1Password secrets manager
- *(security)* Add secret reference manifest
- *(security)* Integrate secrets manager in MCP server
- *(config)* Add configuration template for user customization
- *(cli)* Add Claude Code MCP wrapper script for simplified installation
- *(memory)* Implement batch processing to prevent FalkorDB memory explosions
- *(docker)* Add wrapper script for automatic 1Password token sourcing

### 🐛 Bug Fixes

- *(security)* [**breaking**] Rotate credentials and add secret scanning
- *(network)* Correct OrbStack container networking
- *(config)* Add gitignore exception for configuration template

### 💼 Other

- *(docker)* Add .dockerignore for context optimization

### 🚜 Refactor

- *(tests)* Reorganize test files for cleaner project structure

### 📚 Documentation

- *(docker)* Document optimization results
- *(readme)* Add OrbStack setup instructions
- *(readme)* [**breaking**] Add Claude Code CLI installation instructions
- *(changelog)* Update changelog for v0.2.0
- *(readme)* Update Docker instructions with token handling guidance
- *(changelog)* Update changelog for v1.0.0

### ⚡ Performance

- *(docker)* Optimize Dockerfile for ARM64 builds

### 🧪 Testing

- *(docker)* Add OrbStack test configuration
- *(security)* Add SDK health check script
- *(mocks)* Add test infrastructure for SDK

### ⚙️ Miscellaneous Tasks

- *(git)* Add temp files to gitignore
- *(dev)* Add development setup script
## [0.3.0](https://github.com/adeel/graphiti-claude-code-mcp/compare/v0.2.0..v0.3.0) - 2025-08-27


### 🚀 Features

- *(security)* Add comprehensive 1Password integration testing

### 🐛 Bug Fixes

- *(docker)* Update Langfuse integration path to avoid naming conflicts
- *(imports)* Resolve Langfuse module import conflicts

### 🚜 Refactor

- *(docker)* Migrate to docker compose run for consistency

### 📚 Documentation

- Update changelog for v0.2.0 release
- Update changelog for v0.3.0 release
## [0.2.0](https://github.com/adeel/graphiti-claude-code-mcp/compare/..v0.2.0) - 2025-08-27


### 🚀 Features

- Implement shared memory client with temporal weighting
- Add pattern capture for TDD cycles and solutions
- Implement Claude command generator with memory integration
- Add MCP server with unified memory endpoints
- Add Docker containerization for MCP server deployment
- *(mcp)* Add comprehensive instructions for Claude Code integration
- *(memory)* Add query escaping, token management, and smart indexing
- Add defensive compatibility layer for Graphiti v0.17.9+
- *(observability)* Add Langfuse integration for trace analysis
- *(diagnostics)* Add memory pipeline health check system
- *(security)* Add 1Password integration and improve Docker deployment

### 🐛 Bug Fixes

- Update MCP server imports to match current SDK structure
- *(docker)* Implement cross-platform host detection using environment variable
- Improve MCP server reliability and Docker deployment
- *(docker)* Update networking for OrbStack container communication
- *(mcp)* Add stdio buffering controls for Docker environment
- *(test)* Update Docker test script for OrbStack compatibility
- *(memory)* Wrap search results with computed metadata

### 💼 Other

- Add Docker configuration for containerized deployment

### 🚜 Refactor

- Enforce metadata validation in pattern capture
- Organize test files into tests directory
- *(docs)* Organize documentation into dedicated directory
- *(docker)* Consolidate Dockerfile and improve module verification
- *(core)* Improve MCP server reliability and documentation
- *(structure)* Organize files to keep root directory lean

### 📚 Documentation

- Add comprehensive project documentation and setup guide
- Add Claude Code AI assistant development guide
- Add comprehensive test results and bug documentation
- Update OrbStack configuration documentation

### 🧪 Testing

- Add comprehensive test suite with 15 test cases
- Add verification test for EntityEdge.status fix

### ⚙️ Miscellaneous Tasks

- Initialize project with Python configuration and gitignore
- *(release)* Add git-cliff for automated changelog generation
<!-- generated by git-cliff -->
