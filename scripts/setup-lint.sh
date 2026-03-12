#!/bin/bash
# Setup script for lint environment
# This script installs development dependencies and runs initial lint setup

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[SETUP]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_status "Setting up Python lint environment..."

# Check if we're in a virtual environment
if [[ "$VIRTUAL_ENV" != "" ]]; then
    print_status "Using virtual environment: $VIRTUAL_ENV"
else
    print_status "No virtual environment detected. Consider using one."
fi

# Install development dependencies
print_status "Installing development dependencies..."
pip install -r requirements-dev.txt

# Install pre-commit hooks
print_status "Installing pre-commit hooks..."
pre-commit install

# Run initial format and lint
print_status "Running initial code formatting..."
ruff format src/

print_status "Running initial lint check..."
ruff check src/ --fix

print_success "Lint environment setup completed!"
print_status "You can now run 'make lint' or 'scripts/lint.sh' to check code quality."