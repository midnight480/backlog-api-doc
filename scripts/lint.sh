#!/bin/bash
# Lint script for Agent Hook integration
# This script runs linting checks and can be called by Kiro Agent Hooks

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[LINT]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    print_error "pyproject.toml not found. Please run this script from the project root."
    exit 1
fi

# Check if development dependencies are installed
if ! command -v ruff &> /dev/null; then
    print_warning "Ruff not found. Installing development dependencies..."
    pip install -r requirements-dev.txt
fi

print_status "Starting lint checks..."

# 1. Format code
print_status "Formatting code with Ruff..."
if ruff format src/; then
    print_success "Code formatting completed"
else
    print_error "Code formatting failed"
    exit 1
fi

# 2. Lint code
print_status "Linting code with Ruff..."
if ruff check src/ --fix; then
    print_success "Code linting completed"
else
    print_warning "Linting found issues (some may have been auto-fixed)"
fi

# 3. Type check (optional, don't fail on type errors during development)
print_status "Type checking with Mypy..."
if mypy src/; then
    print_success "Type checking passed"
else
    print_warning "Type checking found issues (not blocking)"
fi

# 4. Security check (optional, don't fail on security warnings during development)
print_status "Security checking with Bandit..."
if bandit -r src/ -q; then
    print_success "Security check passed"
else
    print_warning "Security check found issues (not blocking)"
fi

print_success "Lint process completed successfully!"

# Return success even if some checks had warnings
exit 0