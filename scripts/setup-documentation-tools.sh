#!/bin/bash
# Setup script for documentation and code quality tools

set -e

echo "Setting up Marcus documentation and code quality tools..."

# Check Python version
python_version=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
required_version="3.11"

if [[ $(echo "$python_version < $required_version" | bc) -eq 1 ]]; then
    echo "Error: Python $required_version or higher is required (found $python_version)"
    exit 1
fi

# Install development dependencies
echo "Installing development dependencies..."
pip install -e ".[dev]"

# Install pre-commit hooks
echo "Installing pre-commit hooks..."
pre-commit install
pre-commit install --hook-type commit-msg

# Create baseline for secret detection
echo "Creating secrets baseline..."
detect-secrets scan --baseline .secrets.baseline || true

# Run initial validation
echo "Running initial validation..."
echo "1. Type checking with mypy..."
mypy src/ --config-file pyproject.toml || echo "Note: Type checking found issues to fix"

echo "2. Docstring checking with pydocstyle..."
pydocstyle src/ --config=pyproject.toml || echo "Note: Docstring checking found issues to fix"

echo "3. Code formatting check..."
black --check src/ || echo "Note: Code formatting issues found. Run 'black src/' to fix"

echo "4. Import sorting check..."
isort --check-only src/ || echo "Note: Import sorting issues found. Run 'isort src/' to fix"

echo ""
echo "Setup complete! Documentation tools are now configured."
echo ""
echo "Commands available:"
echo "  - mypy src/                    # Check type hints"
echo "  - pydocstyle src/              # Check docstrings"
echo "  - black src/                   # Format code"
echo "  - isort src/                   # Sort imports"
echo "  - pre-commit run --all-files   # Run all checks"
echo ""
echo "Pre-commit hooks will run automatically on git commit."
echo "To bypass hooks temporarily, use: git commit --no-verify"