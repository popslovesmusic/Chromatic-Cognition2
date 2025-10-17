# Soundlab Φ-Matrix - Release Build System
# Feature 019: Release Readiness Validation

# Version information
VERSION ?= 0.9.0-rc1
BUILD_DATE := $(shell date -u +"%Y-%m-%dT%H:%M:%SZ")
GIT_COMMIT := $(shell git rev-parse --short HEAD 2>/dev/null || echo "unknown")
GIT_TAG := $(shell git describe --tags --exact-match 2>/dev/null || echo "untagged")

# Docker configuration
DOCKER_REGISTRY ?= soundlab
DOCKER_IMAGE := $(DOCKER_REGISTRY)/phi-matrix
DOCKER_TAG := $(VERSION)

# Paths
SERVER_DIR := server
STATIC_DIR := static
DOCS_DIR := docs
BUILD_DIR := build
DIST_DIR := dist

# Python configuration
PYTHON := python3
PIP := pip3
PYTEST := pytest
VENV := .venv

# Colors for output
CYAN := \033[0;36m
GREEN := \033[0;32m
RED := \033[0;31m
NC := \033[0m # No Color

.PHONY: help
help: ## Show this help message
	@echo "$(CYAN)Soundlab Φ-Matrix - Build System$(NC)"
	@echo "$(CYAN)Version: $(VERSION)$(NC)"
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

.PHONY: version
version: ## Show version information
	@echo "Version:    $(VERSION)"
	@echo "Commit:     $(GIT_COMMIT)"
	@echo "Tag:        $(GIT_TAG)"
	@echo "Build Date: $(BUILD_DATE)"

#==============================================================================
# Development Targets
#==============================================================================

.PHONY: install
install: ## Install Python dependencies
	@echo "$(CYAN)Installing dependencies...$(NC)"
	$(PIP) install -r $(SERVER_DIR)/requirements.txt
	@echo "$(GREEN)✓ Dependencies installed$(NC)"

.PHONY: install-dev
install-dev: ## Install development dependencies
	@echo "$(CYAN)Installing development dependencies...$(NC)"
	$(PIP) install -r $(SERVER_DIR)/requirements.txt
	$(PIP) install pytest pytest-asyncio pytest-cov black flake8 mypy
	@echo "$(GREEN)✓ Development dependencies installed$(NC)"

.PHONY: venv
venv: ## Create virtual environment
	@echo "$(CYAN)Creating virtual environment...$(NC)"
	$(PYTHON) -m venv $(VENV)
	@echo "$(GREEN)✓ Virtual environment created at $(VENV)$(NC)"
	@echo "Activate with: source $(VENV)/bin/activate (Linux/Mac) or $(VENV)\Scripts\activate (Windows)"

#==============================================================================
# Testing Targets
#==============================================================================

.PHONY: test
test: ## Run all tests
	@echo "$(CYAN)Running tests...$(NC)"
	cd $(SERVER_DIR) && $(PYTEST) -v --tb=short
	@echo "$(GREEN)✓ Tests passed$(NC)"

.PHONY: test-verbose
test-verbose: ## Run tests with verbose output
	@echo "$(CYAN)Running tests (verbose)...$(NC)"
	cd $(SERVER_DIR) && $(PYTEST) -vv --tb=long

.PHONY: test-cov
test-cov: ## Run tests with coverage
	@echo "$(CYAN)Running tests with coverage...$(NC)"
	cd $(SERVER_DIR) && $(PYTEST) --cov=. --cov-report=html --cov-report=term

.PHONY: test-unit
test-unit: ## Run unit tests only
	@echo "$(CYAN)Running unit tests...$(NC)"
	cd $(SERVER_DIR) && $(PYTEST) -v -m "not integration"

.PHONY: test-integration
test-integration: ## Run integration tests only
	@echo "$(CYAN)Running integration tests...$(NC)"
	cd $(SERVER_DIR) && $(PYTEST) -v -m "integration"

.PHONY: validate
validate: ## Run all validation scripts
	@echo "$(CYAN)Running validation scripts...$(NC)"
	cd $(SERVER_DIR) && $(PYTHON) validate_feature_015.py
	cd $(SERVER_DIR) && $(PYTHON) validate_feature_016.py
	cd $(SERVER_DIR) && $(PYTHON) validate_feature_017.py
	cd $(SERVER_DIR) && $(PYTHON) validate_feature_018.py
	@echo "$(GREEN)✓ All validations passed$(NC)"

#==============================================================================
# Code Quality Targets
#==============================================================================

.PHONY: lint
lint: ## Run linter (flake8)
	@echo "$(CYAN)Running linter...$(NC)"
	cd $(SERVER_DIR) && flake8 --max-line-length=120 --exclude=__pycache__,.venv,venv

.PHONY: format
format: ## Format code with black
	@echo "$(CYAN)Formatting code...$(NC)"
	cd $(SERVER_DIR) && black --line-length=120 .

.PHONY: format-check
format-check: ## Check code formatting
	@echo "$(CYAN)Checking code formatting...$(NC)"
	cd $(SERVER_DIR) && black --line-length=120 --check .

.PHONY: typecheck
typecheck: ## Run type checker (mypy)
	@echo "$(CYAN)Running type checker...$(NC)"
	cd $(SERVER_DIR) && mypy --ignore-missing-imports .

.PHONY: quality
quality: format-check lint typecheck ## Run all quality checks
	@echo "$(GREEN)✓ All quality checks passed$(NC)"

#==============================================================================
# Build Targets
#==============================================================================

.PHONY: clean
clean: ## Clean build artifacts
	@echo "$(CYAN)Cleaning build artifacts...$(NC)"
	rm -rf $(BUILD_DIR) $(DIST_DIR)
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "$(GREEN)✓ Build artifacts cleaned$(NC)"

.PHONY: build
build: clean ## Build release artifacts
	@echo "$(CYAN)Building release artifacts...$(NC)"
	mkdir -p $(BUILD_DIR)
	mkdir -p $(DIST_DIR)
	@echo "VERSION=$(VERSION)" > $(BUILD_DIR)/version.txt
	@echo "GIT_COMMIT=$(GIT_COMMIT)" >> $(BUILD_DIR)/version.txt
	@echo "BUILD_DATE=$(BUILD_DATE)" >> $(BUILD_DIR)/version.txt
	@echo "$(GREEN)✓ Build complete$(NC)"

.PHONY: rc
rc: clean test build ## Build release candidate (FR-001)
	@echo "$(CYAN)Building release candidate $(VERSION)...$(NC)"
	@echo "Running comprehensive validation..."
	$(MAKE) validate
	@echo "Creating release bundle..."
	mkdir -p $(DIST_DIR)/soundlab-$(VERSION)
	cp -r $(SERVER_DIR) $(DIST_DIR)/soundlab-$(VERSION)/
	cp -r $(STATIC_DIR) $(DIST_DIR)/soundlab-$(VERSION)/
	cp -r $(DOCS_DIR) $(DIST_DIR)/soundlab-$(VERSION)/
	cp README.md $(DIST_DIR)/soundlab-$(VERSION)/ 2>/dev/null || true
	cp LICENSE $(DIST_DIR)/soundlab-$(VERSION)/ 2>/dev/null || true
	cp $(BUILD_DIR)/version.txt $(DIST_DIR)/soundlab-$(VERSION)/
	cd $(DIST_DIR) && tar -czf soundlab-$(VERSION).tar.gz soundlab-$(VERSION)
	@echo "$(GREEN)✓ Release candidate built: $(DIST_DIR)/soundlab-$(VERSION).tar.gz$(NC)"
	@echo "$(GREEN)✓ Docker image ready to build with: make docker-build$(NC)"

#==============================================================================
# Docker Targets
#==============================================================================

.PHONY: docker-build
docker-build: ## Build Docker image
	@echo "$(CYAN)Building Docker image...$(NC)"
	docker build \
		--build-arg VERSION=$(VERSION) \
		--build-arg GIT_COMMIT=$(GIT_COMMIT) \
		--build-arg BUILD_DATE=$(BUILD_DATE) \
		-t $(DOCKER_IMAGE):$(DOCKER_TAG) \
		-t $(DOCKER_IMAGE):latest \
		-f Dockerfile .
	@echo "$(GREEN)✓ Docker image built: $(DOCKER_IMAGE):$(DOCKER_TAG)$(NC)"

.PHONY: docker-push
docker-push: ## Push Docker image to registry
	@echo "$(CYAN)Pushing Docker image...$(NC)"
	docker push $(DOCKER_IMAGE):$(DOCKER_TAG)
	docker push $(DOCKER_IMAGE):latest
	@echo "$(GREEN)✓ Docker image pushed$(NC)"

.PHONY: docker-run
docker-run: ## Run Docker container locally
	@echo "$(CYAN)Running Docker container...$(NC)"
	docker run -it --rm \
		-p 8000:8000 \
		-v $(PWD)/logs:/app/logs \
		$(DOCKER_IMAGE):$(DOCKER_TAG)

.PHONY: docker-compose-up
docker-compose-up: ## Start staging environment with docker-compose
	@echo "$(CYAN)Starting staging environment...$(NC)"
	docker-compose -f docker-compose.staging.yml up -d
	@echo "$(GREEN)✓ Staging environment started$(NC)"

.PHONY: docker-compose-down
docker-compose-down: ## Stop staging environment
	@echo "$(CYAN)Stopping staging environment...$(NC)"
	docker-compose -f docker-compose.staging.yml down
	@echo "$(GREEN)✓ Staging environment stopped$(NC)"

.PHONY: docker-compose-logs
docker-compose-logs: ## Show staging logs
	docker-compose -f docker-compose.staging.yml logs -f

#==============================================================================
# Security & Compliance Targets
#==============================================================================

.PHONY: sbom
sbom: ## Generate Software Bill of Materials
	@echo "$(CYAN)Generating SBOM...$(NC)"
	@command -v syft >/dev/null 2>&1 || { echo "$(RED)Error: syft not installed$(NC)"; exit 1; }
	syft packages dir:. -o spdx-json > $(BUILD_DIR)/sbom.spdx.json
	syft packages dir:. -o cyclonedx-json > $(BUILD_DIR)/sbom.cyclonedx.json
	@echo "$(GREEN)✓ SBOM generated: $(BUILD_DIR)/sbom.*.json$(NC)"

.PHONY: security-scan
security-scan: ## Run security scans
	@echo "$(CYAN)Running security scans...$(NC)"
	@command -v safety >/dev/null 2>&1 || $(PIP) install safety
	safety check --json
	@echo "$(GREEN)✓ Security scan complete$(NC)"

.PHONY: license-check
license-check: ## Check license compatibility
	@echo "$(CYAN)Checking licenses...$(NC)"
	@command -v pip-licenses >/dev/null 2>&1 || $(PIP) install pip-licenses
	pip-licenses --format=markdown > $(BUILD_DIR)/licenses.md
	@echo "$(GREEN)✓ License report: $(BUILD_DIR)/licenses.md$(NC)"

#==============================================================================
# Smoke Test Targets
#==============================================================================

.PHONY: smoke
smoke: ## Run smoke tests on staging
	@echo "$(CYAN)Running smoke tests...$(NC)"
	cd smoke && $(PYTHON) smoke_websocket.py
	cd smoke && $(PYTHON) smoke_metrics.py
	cd smoke && $(PYTHON) smoke_presets.py
	@echo "$(GREEN)✓ Smoke tests passed$(NC)"

.PHONY: smoke-staging
smoke-staging: ## Run smoke tests against staging environment
	@echo "$(CYAN)Running smoke tests on staging...$(NC)"
	SOUNDLAB_URL=http://localhost:8000 $(MAKE) smoke

#==============================================================================
# Deployment Targets
#==============================================================================

.PHONY: deploy-staging
deploy-staging: ## Deploy to staging environment
	@echo "$(CYAN)Deploying to staging...$(NC)"
	$(MAKE) docker-compose-up
	sleep 5
	$(MAKE) healthcheck
	@echo "$(GREEN)✓ Deployed to staging$(NC)"

.PHONY: healthcheck
healthcheck: ## Check health endpoints
	@echo "$(CYAN)Checking health endpoints...$(NC)"
	@curl -f http://localhost:8000/healthz || { echo "$(RED)Health check failed$(NC)"; exit 1; }
	@curl -f http://localhost:8000/readyz || { echo "$(RED)Ready check failed$(NC)"; exit 1; }
	@echo "$(GREEN)✓ Health checks passed$(NC)"

.PHONY: rollback
rollback: ## Rollback to previous version
	@echo "$(CYAN)Rolling back...$(NC)"
	docker-compose -f docker-compose.staging.yml down
	docker tag $(DOCKER_IMAGE):previous $(DOCKER_IMAGE):latest
	docker-compose -f docker-compose.staging.yml up -d
	@echo "$(GREEN)✓ Rollback complete$(NC)"

#==============================================================================
# Release Targets
#==============================================================================

.PHONY: tag-release
tag-release: ## Tag release in git
	@echo "$(CYAN)Tagging release $(VERSION)...$(NC)"
	git tag -a $(VERSION) -m "Release $(VERSION)"
	git push origin $(VERSION)
	@echo "$(GREEN)✓ Release tagged: $(VERSION)$(NC)"

.PHONY: release-notes
release-notes: ## Generate release notes
	@echo "$(CYAN)Generating release notes...$(NC)"
	@echo "# Release $(VERSION)" > $(DOCS_DIR)/RELEASE_NOTES.md
	@echo "" >> $(DOCS_DIR)/RELEASE_NOTES.md
	@echo "Build Date: $(BUILD_DATE)" >> $(DOCS_DIR)/RELEASE_NOTES.md
	@echo "Git Commit: $(GIT_COMMIT)" >> $(DOCS_DIR)/RELEASE_NOTES.md
	@echo "" >> $(DOCS_DIR)/RELEASE_NOTES.md
	git log --pretty=format:"- %s (%h)" $(shell git describe --tags --abbrev=0 2>/dev/null)..HEAD >> $(DOCS_DIR)/RELEASE_NOTES.md
	@echo "$(GREEN)✓ Release notes: $(DOCS_DIR)/RELEASE_NOTES.md$(NC)"

.PHONY: go-nogo
go-nogo: ## Run Go/No-Go checklist
	@echo "$(CYAN)Running Go/No-Go checklist...$(NC)"
	cd $(SERVER_DIR) && $(PYTHON) validate_release_readiness.py
	@echo "$(GREEN)✓ Go/No-Go checklist complete$(NC)"

#==============================================================================
# Documentation Targets
#==============================================================================

.PHONY: docs
docs: ## Generate all documentation
	@echo "$(CYAN)Generating documentation...$(NC)"
	@echo "Documentation located in $(DOCS_DIR)/"
	@ls -la $(DOCS_DIR)/
	@echo "$(GREEN)✓ Documentation ready$(NC)"

#==============================================================================
# All-in-One Targets
#==============================================================================

.PHONY: ci
ci: install-dev quality test validate ## Run full CI pipeline
	@echo "$(GREEN)✓ CI pipeline complete$(NC)"

.PHONY: pre-release
pre-release: ci rc sbom license-check ## Prepare for release
	@echo "$(GREEN)✓ Pre-release checks complete$(NC)"

.PHONY: full-release
full-release: pre-release docker-build tag-release release-notes ## Full release process
	@echo "$(GREEN)✓ Full release complete: $(VERSION)$(NC)"
	@echo "Next steps:"
	@echo "  1. Push Docker image: make docker-push"
	@echo "  2. Deploy to staging: make deploy-staging"
	@echo "  3. Run smoke tests: make smoke-staging"
	@echo "  4. Run Go/No-Go: make go-nogo"

#==============================================================================
# Default Target
#==============================================================================

.DEFAULT_GOAL := help
