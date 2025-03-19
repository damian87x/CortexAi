# CortexAi Makefile

# Configuration
VENV := venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
BLACK := $(VENV)/bin/black
ISORT := $(VENV)/bin/isort
MYPY := $(VENV)/bin/mypy
BUILD := $(VENV)/bin/build
TWINE := $(VENV)/bin/twine

# Default target
.PHONY: help
help:
	@echo "CortexAi Makefile"
	@echo "================="
	@echo ""
	@echo "Available targets:"
	@echo "  setup       - Create virtual environment and install dependencies"
	@echo "  install     - Install or update dependencies in existing virtual environment"
	@echo "  clean       - Remove virtual environment and cached files"
	@echo "  test        - Run tests"
	@echo "  format      - Format code with black and isort"
	@echo "  check       - Check code with mypy"
	@echo "  example     - Run basic example"
	@echo "  config      - Run configuration example"
	@echo "  tools       - Run tools demonstration"
	@echo "  basic-tools - Run simplified tools example"
	@echo "  build       - Build distribution packages"
	@echo "  clean-dist  - Remove distribution packages"
	@echo "  test-pypi   - Upload to TestPyPI"
	@echo "  publish     - Upload to PyPI"
	@echo ""
	@echo "Environment variables:"
	@echo "  CONFIG_USE_DOTENV   - Set to 'false' to disable .env file loading (default: true)"
	@echo "  CONFIG_USE_YAML     - Set to 'false' to disable YAML support (default: true)"
	@echo "  CONFIG_ENV_PREFIX   - Set environment variable prefix (default: '')"
	@echo "  CONFIG_LOG_LEVEL    - Set logging level (default: INFO)"

# Setup development environment
.PHONY: setup
setup:
	@bash setup_venv.sh

# Install dependencies in existing virtual environment
.PHONY: install
install: $(VENV)
	$(PIP) install -U pip
	$(PIP) install -e .
	$(PIP) install -e ".[yaml,dev]"
	$(PIP) install build twine

# Create virtual environment
$(VENV):
	python3 -m venv $(VENV)

# Clean up generated files
.PHONY: clean
clean:
	rm -rf $(VENV)
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name "*.egg" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	
# Clean distribution packages
.PHONY: clean-dist
clean-dist:
	rm -rf dist/ build/

# Run tests
.PHONY: test
test: $(VENV)
	$(PYTEST) -xvs

# Format code
.PHONY: format
format: $(VENV)
	$(BLACK) .
	$(ISORT) .

# Type checking
.PHONY: check
check: $(VENV)
	$(MYPY) CortexAi examples

# Run basic example
.PHONY: example
example: $(VENV)
	$(PYTHON) examples/basic_usage.py

# Run config example
.PHONY: config
config: $(VENV)
	CONFIG_LOG_LEVEL=DEBUG $(PYTHON) examples/simple_config_demo.py

# Run tools demonstration
.PHONY: tools
tools: $(VENV)
	$(PYTHON) examples/tools_demo.py

# Run simplified tools example
.PHONY: basic-tools
basic-tools: $(VENV)
	$(PYTHON) examples/basic_tools_example.py

# Build package
.PHONY: build
build: clean-dist $(VENV)
	$(BUILD) --sdist --wheel

# Upload to TestPyPI
.PHONY: test-pypi
test-pypi: build
	$(TWINE) upload --repository testpypi dist/*

# Upload to PyPI
.PHONY: publish
publish: build
	$(TWINE) upload dist/*
