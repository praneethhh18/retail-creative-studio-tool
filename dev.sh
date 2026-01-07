#!/usr/bin/env bash
# Development helper script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[*]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[x]${NC} $1"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Install backend dependencies
install_backend() {
    print_status "Installing backend dependencies..."
    cd backend
    
    if [ ! -d "venv" ]; then
        python -m venv venv
    fi
    
    source venv/bin/activate
    pip install -r requirements.txt
    pip install pytest pytest-cov black flake8 mypy
    
    cd ..
    print_status "Backend dependencies installed!"
}

# Install frontend dependencies
install_frontend() {
    print_status "Installing frontend dependencies..."
    cd frontend
    npm install
    npx playwright install chromium
    cd ..
    print_status "Frontend dependencies installed!"
}

# Run backend
run_backend() {
    print_status "Starting backend server..."
    cd backend
    source venv/bin/activate
    uvicorn app.main:app --reload --port 8000
}

# Run frontend
run_frontend() {
    print_status "Starting frontend dev server..."
    cd frontend
    npm run dev
}

# Run tests
run_tests() {
    print_status "Running all tests..."
    
    print_status "Backend tests..."
    cd backend
    source venv/bin/activate
    pytest tests/ -v --cov=app
    cd ..
    
    print_status "Frontend tests..."
    cd frontend
    npm run test:unit
    cd ..
    
    print_status "All tests completed!"
}

# Lint code
lint() {
    print_status "Linting code..."
    
    print_status "Backend linting..."
    cd backend
    source venv/bin/activate
    black app --check
    flake8 app --max-line-length=120
    cd ..
    
    print_status "Frontend linting..."
    cd frontend
    npm run lint
    cd ..
    
    print_status "Linting completed!"
}

# Docker build and run
docker_up() {
    print_status "Building and starting Docker containers..."
    docker-compose up --build
}

docker_down() {
    print_status "Stopping Docker containers..."
    docker-compose down
}

# Show help
show_help() {
    echo "Retail Creative Tool - Development Helper"
    echo ""
    echo "Usage: ./dev.sh [command]"
    echo ""
    echo "Commands:"
    echo "  install-backend   Install Python dependencies"
    echo "  install-frontend  Install Node.js dependencies"
    echo "  install           Install all dependencies"
    echo "  backend           Start backend development server"
    echo "  frontend          Start frontend development server"
    echo "  test              Run all tests"
    echo "  lint              Lint all code"
    echo "  docker-up         Build and start Docker containers"
    echo "  docker-down       Stop Docker containers"
    echo "  help              Show this help message"
}

# Main
case "$1" in
    install-backend)
        install_backend
        ;;
    install-frontend)
        install_frontend
        ;;
    install)
        install_backend
        install_frontend
        ;;
    backend)
        run_backend
        ;;
    frontend)
        run_frontend
        ;;
    test)
        run_tests
        ;;
    lint)
        lint
        ;;
    docker-up)
        docker_up
        ;;
    docker-down)
        docker_down
        ;;
    help|--help|-h|"")
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
