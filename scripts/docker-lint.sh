#!/bin/bash
# Docker-based lint script
# Runs linting in a clean Docker environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[DOCKER-LINT]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_status "Running linting in Docker container..."

# Create a temporary Dockerfile for linting
cat > Dockerfile.lint << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

# Copy source code
COPY src/ ./src/
COPY pyproject.toml mypy.ini ./

# Run linting
CMD ["bash", "-c", "ruff format src/ && ruff check src/ && mypy src/ && bandit -r src/"]
EOF

# Build and run the linting container
if docker build -f Dockerfile.lint -t backlog-api-lint .; then
    print_status "Docker image built successfully"
else
    print_error "Failed to build Docker image"
    rm -f Dockerfile.lint
    exit 1
fi

if docker run --rm backlog-api-lint; then
    print_success "Docker linting completed successfully"
    RESULT=0
else
    print_error "Docker linting failed"
    RESULT=1
fi

# Cleanup
rm -f Dockerfile.lint
docker rmi backlog-api-lint 2>/dev/null || true

exit $RESULT