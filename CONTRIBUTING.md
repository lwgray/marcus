# Contributing to PM Agent

Welcome to PM Agent! We're excited you're interested in contributing. This guide will help you get started, whether you're fixing a typo or building a major feature.

## 🌟 First Time Contributing?

New to open source? PM Agent is a great place to start! Here's how:

### Quick Start for First-Timers

1. **Find a Good First Issue**
   - Look for issues labeled [`good first issue`](https://github.com/lwgray/pm-agent/labels/good%20first%20issue)
   - These are specifically chosen to be approachable for newcomers
   - Don't see one you like? Ask in discussions - we'll help you find something!

2. **Set Up Your Environment** (15 minutes)
   ```bash
   # Fork the repo on GitHub (click the Fork button)
   # Then clone your fork:
   git clone https://github.com/YOUR_USERNAME/pm-agent.git
   cd pm-agent

   # Set up development environment
   ./scripts/dev-setup.sh  # This handles everything for you!
   ```

3. **Make Your First Contribution**
   - Start small: fix a typo, improve an error message, or add a test
   - Even tiny improvements are valuable!
   - Your first PR doesn't need to be perfect - we'll help you improve it

### Your First Pull Request Checklist

- [ ] I've read the Quick Start section
- [ ] I've set up my development environment
- [ ] I've found an issue to work on (or created one)
- [ ] I've made my changes in a new branch
- [ ] I've tested my changes work
- [ ] I've opened a Pull Request
- [ ] I'm ready to learn from feedback!

## 🤝 Code of Conduct

We're committed to providing a welcoming and inspiring community for all. Before participating, please read our code of conduct:

- **Be Respectful**: Value each other's ideas, styles, and viewpoints
- **Be Supportive**: Be kind to newcomers and help them learn
- **Be Collaborative**: Work together to solve problems
- **Be Inclusive**: Welcome people of all backgrounds and identities
- **Be Professional**: Disagreement is fine, but stay constructive

## 🛠️ Ways to Contribute

### Not Just Code!

PM Agent needs more than just code contributions:

- 📝 **Documentation**: Help others understand PM Agent better
- 🎨 **Design**: Improve UI/UX, create diagrams, or design assets
- 🧪 **Testing**: Write tests, find bugs, or improve test coverage
- 💬 **Community**: Answer questions, write tutorials, or give talks
- 🌐 **Translation**: Help make PM Agent accessible globally
- 💡 **Ideas**: Suggest features, improvements, or use cases

### Code Contributions

#### Reporting Bugs

Found a bug? Help us fix it:

1. **Check Existing Issues**: Maybe someone already reported it
2. **Create a Bug Report**: Use our bug report template
3. **Include Details**:
   - What you expected to happen
   - What actually happened
   - Steps to reproduce
   - Your environment (OS, Python version, etc.)
   - Error messages and logs

#### Suggesting Features

Have an idea? We'd love to hear it:

1. **Check the Roadmap**: See if it's already planned
2. **Open a Discussion**: Get community feedback first
3. **Create a Feature Request**: Use our template
4. **Explain the Why**: Help us understand the problem it solves

#### Submitting Code

Ready to code? Follow these steps:

1. **Claim an Issue**: Comment "I'll work on this" to avoid duplicate work
2. **Fork and Branch**: Create a feature branch from `main`
3. **Write Code**: Follow our style guide (see below)
4. **Add Tests**: New features need tests
5. **Update Docs**: If you changed behavior, update the docs
6. **Submit PR**: Use our PR template

## 💻 Development Setup

### Prerequisites

- Python 3.10 or higher
- Docker (for running Planka locally)
- Git

### Detailed Setup

```bash
# 1. Fork and clone
git clone https://github.com/YOUR_USERNAME/pm-agent.git
cd pm-agent

# 2. Add upstream remote (to stay updated)
git remote add upstream https://github.com/lwgray/pm-agent.git

# 3. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 5. Install pre-commit hooks
pre-commit install

# 6. Set up environment variables
cp .env.example .env
# Edit .env with your settings

# 7. Run tests to verify setup
pytest

# 8. Start PM Agent locally
./start.sh demo  # Runs with mock agents
```

### Development Workflow

```bash
# 1. Update your fork
git checkout main
git pull upstream main
git push origin main

# 2. Create feature branch
git checkout -b feature/your-feature-name

# 3. Make changes and test
# ... edit files ...
pytest tests/  # Run tests
black src/     # Format code
flake8 src/    # Check style

# 4. Commit with conventional commits
git add .
git commit -m "feat(worker): add task retry logic"

# 5. Push and create PR
git push origin feature/your-feature-name
# Open PR on GitHub
```

## 📋 Coding Standards

### Python Style Guide

We follow PEP 8 with these additions:

```python
# Good: Clear, typed, documented
def assign_task(agent_id: str, task_id: str, priority: int = 1) -> TaskAssignment:
    """
    Assign a task to an agent with optional priority.

    Args:
        agent_id: Unique identifier of the agent
        task_id: Unique identifier of the task
        priority: Task priority (1-5, default 1)

    Returns:
        TaskAssignment object with assignment details

    Raises:
        AgentNotFoundError: If agent doesn't exist
        TaskNotFoundError: If task doesn't exist
    """
    # Implementation here
    pass

# Bad: Unclear, untyped, undocumented
def assign(a, t, p=1):
    # assigns task
    pass
```

### Best Practices

1. **Type Hints**: Always use type hints for function arguments and returns
2. **Docstrings**: Every public function/class needs a docstring
3. **Error Handling**: Use specific exceptions, not generic ones
4. **Logging**: Use structured logging, not print statements
5. **Constants**: Define at module level in UPPER_CASE
6. **Tests**: Aim for 80% coverage, test edge cases

### Commit Messages

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style (formatting, semicolons, etc)
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `perf`: Performance improvement
- `test`: Adding or correcting tests
- `chore`: Maintenance tasks

**Examples**:
```bash
# Good examples
git commit -m "feat(worker): add exponential backoff for retries"
git commit -m "fix(kanban): handle GitHub API rate limits"
git commit -m "docs(concepts): add MCP protocol explanation"

# Bad examples
git commit -m "fixed stuff"
git commit -m "WIP"
git commit -m "updates"
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_task_manager.py

# Run specific test
pytest tests/unit/test_task_manager.py::test_assign_task

# Run only fast tests
pytest -m "not slow"
```

### Writing Tests

```python
# Good test example
def test_agent_registration_with_valid_data():
    """Test that agents can register with valid data."""
    # Arrange
    agent_data = {
        "agent_id": "test-001",
        "name": "Test Agent",
        "skills": ["python", "testing"]
    }

    # Act
    result = agent_manager.register_agent(agent_data)

    # Assert
    assert result.success is True
    assert result.agent.id == "test-001"
    assert "python" in result.agent.skills

# Use fixtures for common setup
@pytest.fixture
def mock_agent():
    return Agent(
        id="test-001",
        name="Test Agent",
        skills=["python", "testing"]
    )
```

### Test Categories

- **Unit Tests**: Test individual functions/classes in isolation
- **Integration Tests**: Test component interactions
- **End-to-End Tests**: Test complete workflows
- **Performance Tests**: Ensure code meets performance requirements

## 📚 Documentation

### When to Update Docs

Update documentation when you:
- Add a new feature
- Change existing behavior
- Fix a confusing part of the docs
- Add a new example or tutorial

### Documentation Structure

```
docs/
├── concepts/        # Explanations of key concepts
├── how-to/         # Step-by-step guides
├── reference/      # API and configuration reference
├── tutorials/      # Learning-oriented content
└── templates/      # Templates for new docs
```

### Writing Good Documentation

```markdown
# Good: Clear, structured, helpful
## How to Configure GitHub Provider

To use GitHub as your kanban provider, follow these steps:

1. **Get a GitHub Token**
   - Go to Settings > Developer settings > Personal access tokens
   - Click "Generate new token"
   - Select scopes: `repo`, `project`

2. **Set Environment Variables**
   ```bash
   export KANBAN_PROVIDER=github
   export GITHUB_TOKEN=ghp_xxxxxxxxxxxx
   export GITHUB_PROJECT_URL=https://github.com/users/YOU/projects/1
   ```

3. **Verify Connection**
   ```bash
   python -m marcus verify-connection
   ```

# Bad: Vague, unstructured
## GitHub Setup
You need a token and project URL. Set them in the environment.
```

## 🔄 Pull Request Process

### Before Submitting

- [ ] Tests pass locally (`pytest`)
- [ ] Code is formatted (`black src/`)
- [ ] Code passes linting (`flake8 src/`)
- [ ] Documentation is updated
- [ ] Commit messages follow convention
- [ ] PR description explains the change

### PR Template

When you open a PR, you'll see our template. Fill it out completely:

```markdown
## Description
Brief description of what this PR does

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] My code follows the style guide
- [ ] I've added tests for my changes
- [ ] I've updated relevant documentation
```

### Review Process

1. **Automated Checks**: CI runs tests, linting, and security checks
2. **Code Review**: Maintainers review for quality and fit
3. **Feedback**: Address any requested changes
4. **Approval**: Once approved, we'll merge your PR!

### After Your PR is Merged

- Delete your feature branch
- Update your fork's main branch
- Celebrate! You've contributed to PM Agent! 🎉

## 🎯 Areas Needing Help

Looking for something to work on? These areas need attention:

### High Priority
- 🧪 **Test Coverage**: Especially integration tests
- 📚 **Documentation**: Tutorials and examples
- 🐛 **Bug Fixes**: Check the issue tracker
- 🔧 **Provider Support**: Add support for new kanban boards

### Feature Ideas
- 📊 Better progress visualization
- 🔌 More MCP tool implementations
- 🌐 Internationalization support
- 📱 Mobile-friendly dashboard

## 💬 Getting Help

### Where to Ask Questions

- **GitHub Discussions**: For general questions and ideas
- **Issue Comments**: For specific issues
- **Discord**: [Join our community](https://discord.gg/pm-agent) (coming soon)

### Tips for Getting Help

1. **Search First**: Check docs, issues, and discussions
2. **Be Specific**: Include error messages, code samples, and context
3. **Show Your Work**: Explain what you've already tried
4. **Be Patient**: Maintainers are volunteers

## 🏆 Recognition

We value all contributions! Contributors are recognized in:

- `CONTRIBUTORS.md` file (automatic)
- Release notes (for significant contributions)
- Project README (for major contributors)
- Special badges/roles in Discord

## 📖 Additional Resources

### Learn More About PM Agent
- [Architecture Overview](/docs/concepts/architecture)
- [Worker Agents Explained](/docs/concepts/worker-agents)
- [MCP Protocol Guide](/docs/concepts/mcp-protocol)
- [Contribution Examples & Case Studies](/docs/contributing/contribution-examples) - Real examples to inspire you!

### Improve Your Skills
- [Python Testing Guide](https://realpython.com/python-testing/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [How to Write Good Documentation](https://www.writethedocs.org/guide/)

### Tools We Use
- [Black](https://black.readthedocs.io/) - Code formatter
- [Pytest](https://docs.pytest.org/) - Testing framework
- [Pre-commit](https://pre-commit.com/) - Git hooks
- [MkDocs](https://www.mkdocs.org/) - Documentation

---

## Thank You!

Every contribution makes PM Agent better. Whether it's your first open source contribution or your thousandth, we're grateful you're here.

Welcome to the PM Agent community! 🚀
