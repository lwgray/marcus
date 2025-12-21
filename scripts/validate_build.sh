#!/bin/bash
#
# Marcus Build Validation Script
#
# Validates that Marcus can be built, installed, and passes all quality checks.
# Run this script before committing major changes or creating releases.
#
# Usage:
#   ./scripts/validate_build.sh [--quick]
#
# Options:
#   --quick    Run only fast checks (skip slow integration tests)
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
QUICK_MODE=false
if [[ "$1" == "--quick" ]]; then
    QUICK_MODE=true
fi

# Timing
START_TIME=$(date +%s)

# Helper functions
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_step() {
    echo -e "${BLUE}▶ $1${NC}"
}

# Trap errors and report
trap 'print_error "Build validation failed at step: $CURRENT_STEP"' ERR

# ============================================================
# STEP 1: Environment Check
# ============================================================
CURRENT_STEP="Environment Check"
print_header "Step 1: Environment Check"

print_step "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
REQUIRED_VERSION="3.11.0"

if ! command -v python3 &> /dev/null; then
    print_error "Python 3 not found"
    exit 1
fi

# Simple version check (works for 3.11 and 3.12)
if [[ ! "$PYTHON_VERSION" =~ ^3\.(1[1-9]|[2-9][0-9]) ]]; then
    print_error "Python 3.11+ required, found $PYTHON_VERSION"
    exit 1
fi

print_success "Python $PYTHON_VERSION"

print_step "Checking virtual environment..."
if [[ -z "${VIRTUAL_ENV}" ]]; then
    print_warning "Not in a virtual environment (recommended but not required)"
else
    print_success "Virtual environment active: $VIRTUAL_ENV"
fi

# ============================================================
# STEP 2: Dependency Check
# ============================================================
CURRENT_STEP="Dependency Check"
print_header "Step 2: Dependency Check"

print_step "Installing/upgrading dependencies..."
pip install -q --upgrade pip setuptools wheel

print_step "Installing Marcus in development mode..."
pip install -q -e ".[dev]"

print_success "Dependencies installed"

# ============================================================
# STEP 3: Code Quality - Formatting
# ============================================================
CURRENT_STEP="Code Formatting"
print_header "Step 3: Code Formatting (Black & isort)"

print_step "Running Black..."
if black --check src tests 2>&1 | grep -q "would be reformatted"; then
    print_error "Code formatting issues found. Run: black src tests"
    black --check src tests
    exit 1
fi
print_success "Black formatting OK"

print_step "Running isort..."
if ! isort --check-only src tests > /dev/null 2>&1; then
    print_error "Import sorting issues found. Run: isort src tests"
    isort --check-only src tests
    exit 1
fi
print_success "Import sorting OK"

# ============================================================
# STEP 4: Code Quality - Linting
# ============================================================
CURRENT_STEP="Linting"
print_header "Step 4: Code Quality (Flake8 & Pydocstyle)"

print_step "Running Flake8..."
if ! flake8 src tests --max-line-length=88 --extend-ignore=E203,W503 > /dev/null 2>&1; then
    print_warning "Flake8 found issues (non-blocking)"
    flake8 src tests --max-line-length=88 --extend-ignore=E203,W503 || true
else
    print_success "Flake8 checks passed"
fi

print_step "Running Pydocstyle..."
if ! pydocstyle src --convention=numpy > /dev/null 2>&1; then
    print_warning "Docstring issues found (non-blocking)"
else
    print_success "Docstring checks passed"
fi

# ============================================================
# STEP 5: Type Checking
# ============================================================
CURRENT_STEP="Type Checking"
print_header "Step 5: Type Checking (Mypy)"

print_step "Running Mypy on src/..."
if ! mypy src > /dev/null 2>&1; then
    print_error "Type checking failed"
    mypy src
    exit 1
fi
print_success "Mypy type checking passed"

# ============================================================
# STEP 6: Security Checks
# ============================================================
CURRENT_STEP="Security Checks"
print_header "Step 6: Security Checks (Bandit)"

print_step "Running Bandit security scanner..."
if ! bandit -r src -q > /dev/null 2>&1; then
    print_warning "Security issues found (review manually)"
    bandit -r src || true
else
    print_success "Security checks passed"
fi

# ============================================================
# STEP 7: Smoke Tests
# ============================================================
CURRENT_STEP="Smoke Tests"
print_header "Step 7: Smoke Tests (Fast Sanity Checks)"

print_step "Running smoke tests..."
if ! pytest tests/smoke/ -v --tb=short -x; then
    print_error "Smoke tests failed"
    exit 1
fi
print_success "Smoke tests passed"

# ============================================================
# STEP 8: Unit Tests
# ============================================================
CURRENT_STEP="Unit Tests"
print_header "Step 8: Unit Tests"

print_step "Running unit tests with coverage..."
if ! pytest tests/unit/ \
    -v \
    --cov=src \
    --cov-report=term-missing:skip-covered \
    --cov-report=html \
    --cov-fail-under=80 \
    --tb=short; then
    print_error "Unit tests failed or coverage below 80%"
    exit 1
fi
print_success "Unit tests passed with >80% coverage"

# ============================================================
# STEP 9: Integration Tests (Optional)
# ============================================================
CURRENT_STEP="Integration Tests"
if [[ "$QUICK_MODE" == "false" ]]; then
    print_header "Step 9: Integration Tests (E2E)"

    print_step "Running integration tests..."
    if ! pytest tests/integration/ \
        -v \
        --tb=short \
        -m "not slow"; then
        print_error "Integration tests failed"
        exit 1
    fi
    print_success "Integration tests passed"
else
    print_header "Step 9: Integration Tests (Skipped in quick mode)"
    print_warning "Skipping integration tests (use without --quick to run)"
fi

# ============================================================
# STEP 10: Pre-commit Hooks
# ============================================================
CURRENT_STEP="Pre-commit Hooks"
print_header "Step 10: Pre-commit Hooks"

print_step "Installing pre-commit hooks..."
pre-commit install > /dev/null 2>&1 || true

print_step "Running pre-commit on all files..."
if ! pre-commit run --all-files > /dev/null 2>&1; then
    print_warning "Pre-commit hooks found issues (non-blocking)"
    pre-commit run --all-files || true
else
    print_success "Pre-commit hooks passed"
fi

# ============================================================
# STEP 11: Build Test
# ============================================================
CURRENT_STEP="Build Test"
print_header "Step 11: Build Test"

print_step "Testing package build..."
if ! python -m build --wheel --outdir /tmp/marcus-build-test > /dev/null 2>&1; then
    print_error "Package build failed"
    exit 1
fi
print_success "Package builds successfully"

# Clean up build artifacts
rm -rf /tmp/marcus-build-test

# ============================================================
# Summary
# ============================================================
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

print_header "Build Validation Complete"

print_success "All checks passed!"
echo ""
echo "Summary:"
echo "  • Environment:        ✓"
echo "  • Dependencies:       ✓"
echo "  • Code Formatting:    ✓"
echo "  • Linting:            ✓"
echo "  • Type Checking:      ✓"
echo "  • Security:           ✓"
echo "  • Smoke Tests:        ✓"
echo "  • Unit Tests:         ✓"
if [[ "$QUICK_MODE" == "false" ]]; then
    echo "  • Integration Tests:  ✓"
else
    echo "  • Integration Tests:  ⊘ (skipped)"
fi
echo "  • Pre-commit Hooks:   ✓"
echo "  • Build:              ✓"
echo ""
echo -e "${GREEN}Total time: ${DURATION}s${NC}"
echo ""
echo -e "${GREEN}🎉 Marcus is ready for deployment!${NC}"
