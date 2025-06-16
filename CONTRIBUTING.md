# Contributing to PM Agent

Thank you for your interest in contributing to PM Agent! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct:
- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive criticism
- Respect differing viewpoints and experiences

## How to Contribute

### Reporting Issues

1. Check existing issues to avoid duplicates
2. Use issue templates when available
3. Provide clear descriptions and steps to reproduce
4. Include relevant logs and error messages

### Suggesting Enhancements

1. Open a discussion first for major changes
2. Clearly describe the proposed enhancement
3. Explain the use case and benefits
4. Consider backward compatibility

### Pull Requests

1. Fork the repository
2. Create a feature branch from `main`
3. Make your changes
4. Add/update tests
5. Update documentation
6. Submit a pull request

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/pm-agent.git
cd pm-agent

# Add upstream remote
git remote add upstream https://github.com/lwgray/pm-agent.git

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## Development Guidelines

### Code Style

- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Add type hints where appropriate
- Keep functions focused and small

### Testing

- Write tests for new features
- Ensure all tests pass before submitting PR
- Aim for 80% code coverage
- Use meaningful test names

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test
pytest tests/unit/test_models.py::test_agent_registration
```

### Documentation

- Update relevant documentation
- Add docstrings to new functions/classes
- Include examples where helpful
- Keep README.md up to date

### Commit Messages

Follow conventional commits format:

```
type(scope): subject

body (optional)

footer (optional)
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Test additions/changes
- `refactor`: Code refactoring
- `style`: Code style changes
- `chore`: Maintenance tasks

Example:
```
feat(worker): add retry logic for failed tasks

Implement exponential backoff for task retries when workers
encounter transient failures. Maximum 3 retries with delays
of 1s, 2s, and 4s.

Closes #123
```

## Project Structure

```
pm-agent/
├── src/               # Source code
│   ├── core/         # Core business logic
│   ├── integrations/ # External integrations
│   └── ...
├── tests/            # Test suite
├── scripts/          # Utility scripts
├── docs/            # Documentation
└── config/          # Configuration files
```

## Testing Guidelines

### Unit Tests
- Test individual functions/methods
- Mock external dependencies
- Focus on edge cases

### Integration Tests
- Test component interactions
- Use real kanban-mcp connection
- Verify end-to-end workflows

### Test Organization
```python
# tests/unit/test_models.py
class TestAgent:
    def test_registration(self):
        """Test agent registration process"""
        pass
    
    def test_capability_matching(self):
        """Test skill matching logic"""
        pass
```

## Documentation Standards

### Docstrings
```python
def assign_task(agent_id: str, task_id: str) -> dict:
    """
    Assign a task to an agent.
    
    Args:
        agent_id: Unique identifier of the agent
        task_id: Unique identifier of the task
        
    Returns:
        dict: Assignment details including status
        
    Raises:
        ValueError: If agent or task not found
    """
```

### API Documentation
- Document all MCP tools
- Include parameter descriptions
- Provide usage examples
- Note any limitations

## Review Process

1. Automated checks run on PR
2. Code review by maintainers
3. Address feedback
4. Approval and merge

## Release Process

1. Version bump following semver
2. Update CHANGELOG.md
3. Create release notes
4. Tag release
5. Deploy to package registry

## Getting Help

- 💬 Open a discussion for questions
- 📧 Email maintainers for sensitive issues
- 📚 Check documentation first
- 🤝 Join our community chat

## Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project documentation

Thank you for contributing to PM Agent! 🎉