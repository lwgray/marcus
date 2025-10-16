# Contributing to Marcus

Welcome to Marcus! We're excited you're interested in contributing. This guide will help you get started, whether you're fixing a typo or building a major feature.

## 💰 Zero-Cost Development (No API Keys Needed!)

**You can contribute to Marcus 100% FREE** - no paid API keys required!

Marcus supports local AI models through Ollama. The recommended free setup:

```bash
# 1. Install Ollama (one-time, 2 minutes)
curl -fsSL https://ollama.com/install.sh | sh

# 2. Pull Qwen2.5-Coder (best free coding model, ~5GB download)
ollama pull qwen2.5-coder:7b

# 3. Use the free development config
cp .env.dev.example .env

# 4. Start developing!
./marcus start
```

**Why Qwen2.5-Coder?**
- ✅ **Free & Open Source** - No costs, ever
- ✅ **Excellent Code Quality** - Rivals GPT-4 for coding tasks
- ✅ **Runs Locally** - Works on 8GB RAM, no internet needed
- ✅ **Fast Responses** - No API latency
- ✅ **Privacy First** - Your code never leaves your machine

📖 **Full guide:** [Setup Local LLM](docs/source/getting-started/setup-local-llm.md)

**Alternative free models:**
- `deepseek-coder:6.7b` - Excellent code understanding
- `codellama:7b` - Fast responses
- `mistral:7b` - Good general purpose

> **💡 Tip:** All Marcus features work identically with local or cloud models!

## 🔀 Branching Strategy

**Important:** Marcus uses a `develop` branch workflow to manage contributions efficiently.

- **`main`**: Production-ready code. Protected - no direct pushes allowed.
- **`develop`**: Primary development branch. All PRs should target this branch.
- **Feature branches**: Work in your fork's feature branches, created from `develop`.

**Why this approach?**
- ✅ Reduces merge conflicts by keeping all development synchronized
- ✅ Allows testing before production release
- ✅ Keeps your fork clean and organized
- ✅ Makes it easy to stay up-to-date with latest changes

**Quick workflow:**
1. Fork the Marcus repository
2. Clone your fork and add upstream remote
3. Always branch from `develop`
4. Submit PRs targeting `develop`

## 🌟 First Time Contributing?

New to open source? Marcus is a great place to start! Here's how:

### Quick Start for First-Timers

1. **Find a Good First Issue**
   - Look for issues labeled [`good first issue`](https://github.com/lwgray/marcus/labels/good%20first%20issue)
   - These are specifically chosen to be approachable for newcomers
   - Don't see one you like? Ask in discussions - we'll help you find something!

2. **Set Up Your Environment** (15 minutes)

   📖 **See the complete guide:** [Local Development Setup](docs/source/developer/local-development.md)

   **Quick overview:**
   ```bash
   # 1. Fork the repo on GitHub (click the Fork button)
   # Then clone your fork and kanban-mcp as sibling directories:
   cd ~/projects  # or wherever you prefer
   git clone https://github.com/YOUR_USERNAME/marcus.git
   git clone https://github.com/lwgray/kanban-mcp.git

   # 2. Build kanban-mcp
   cd kanban-mcp
   npm install && npm run build

   # 3. Set up Marcus
   cd ../marcus
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   pre-commit install

   # 4. Start Planka (in Docker)
   docker compose up -d postgres planka

   # 5. Configure Marcus
   cp config_marcus.example.json config_marcus.json
   # Edit with your Planka project/board IDs and API key

   # 6. Run tests to verify setup
   pytest tests/
   ```

3. **Make Your First Contribution**
   - Start small: fix a typo, improve an error message, or add a test
   - Even tiny improvements are valuable!
   - Your first PR doesn't need to be perfect - we'll help you improve it

### Your First Pull Request Checklist

- [ ] I've read the [Local Development Setup](docs/source/developer/local-development.md)
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

Marcus needs more than just code contributions:

- 📝 **Documentation**: Help others understand Marcus better
- 🎨 **Design**: Improve UI/UX, create diagrams, or design assets
- 🧪 **Testing**: Write tests, find bugs, or improve test coverage
- 💬 **Community**: Answer questions, write tutorials, or give talks
- 🌐 **Translation**: Help make Marcus accessible globally
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
   - Your environment (OS, Python version, Docker version, etc.)
   - Error messages and logs

#### Suggesting Features

Have an idea? We'd love to hear it:

1. **Check the Roadmap**: See [docs/source/roadmap/](docs/source/roadmap/) if it's already planned
2. **Open a Discussion**: Get community feedback first
3. **Create a Feature Request**: Use our template
4. **Explain the Why**: Help us understand the problem it solves

#### Submitting Code

Ready to code? Follow these steps:

1. **Claim an Issue**: Comment "I'll work on this" to avoid duplicate work
2. **Fork and Branch**: Create a feature branch from `develop` in your fork
3. **Write Code**: Follow our style guide (see below)
4. **Add Tests**: New features need tests (80% coverage target)
5. **Update Docs**: If you changed behavior, update the docs
6. **Keep Updated**: Regularly sync with `upstream/develop` to avoid conflicts
7. **Submit PR**: Use our PR template and target the `develop` branch

## 💻 Development Setup

### Prerequisites

- Python 3.11 or higher
- Docker and Docker Compose (for running Planka)
- Git
- Node.js 16+ (for kanban-mcp)
- AI Model (choose one):
  - **FREE:** Ollama with Qwen2.5-Coder (recommended for contributors, see above ⬆️)
  - **Paid:** Anthropic or OpenAI API key

### Detailed Setup

📖 **Complete guide:** [Local Development Setup](docs/source/developer/local-development.md)

**Quick setup:**

```bash
# 1. Clone Marcus and kanban-mcp as sibling directories
cd ~/projects
git clone https://github.com/YOUR_USERNAME/marcus.git
git clone https://github.com/lwgray/kanban-mcp.git

# 2. Add upstream remote and checkout develop
cd marcus
git remote add upstream https://github.com/lwgray/marcus.git
git checkout develop

# 3. Build kanban-mcp
cd ../kanban-mcp
npm install && npm run build

# 4. Set up Marcus virtual environment
cd ../marcus
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 5. Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 6. Install pre-commit hooks (required for code quality)
pre-commit install

# 7. Start Planka
docker compose up -d postgres planka

# 8. Configure Marcus
cp config_marcus.example.json config_marcus.json
# Edit config_marcus.json with your Planka project/board IDs and API key

# 9. Run tests to verify setup
pytest tests/
```

### Development Workflow

📖 **Complete guide:** [Development Workflow](docs/source/developer/development-workflow.md)

**Important:** Marcus uses a `develop` branch workflow. All contributions should be made against `develop`, not `main`.

```bash
# 1. Set up upstream remote (one-time setup)
git remote add upstream https://github.com/lwgray/marcus.git

# 2. Update your fork's develop branch
git checkout develop
git pull upstream develop
git push origin develop

# 3. Create feature branch from develop (in your fork)
git checkout -b feature/your-feature-name

# 4. Make changes and test
# ... edit files ...
pytest tests/                    # Run tests
mypy src/                        # Type checking
pre-commit run --all-files       # Run all quality checks

# 5. Commit with conventional commits
git add .
git commit -m "feat(worker): add task retry logic"

# 6. Keep your branch updated with develop
git fetch upstream
git rebase upstream/develop

# 7. Push to your fork and create PR
git push origin feature/your-feature-name
# Open PR on GitHub targeting the 'develop' branch
```

**Branching Best Practices:**
- ✅ Always branch from `develop`, not `main`
- ✅ Work in your fork's feature branches
- ✅ Keep feature branches focused and short-lived
- ✅ Regularly sync with `upstream/develop` to avoid conflicts
- ✅ Target your PRs to the `develop` branch

### Running Marcus Locally vs Docker

📖 **See:** [Development Workflow - Testing Workflow](docs/source/developer/development-workflow.md#testing-workflow)

```bash
# Local (faster iteration)
./marcus start

# Docker (production-like)
docker compose up -d marcus
docker compose logs -f marcus
```

## ✅ Code Quality and Pre-Commit

We use pre-commit hooks to ensure consistent code quality. These run automatically before every commit.

### Pre-Commit Hooks

Our pre-commit configuration includes:

- **MyPy**: Static type checking to catch type errors
- **Ruff**: Fast Python linter for code quality
- **Black**: Code formatter for consistent style
- **isort**: Import statement organizer
- **detect-secrets**: Prevents committing secrets and API keys
- **YAML/JSON validation**: Ensures configuration files are valid
- **Trailing whitespace removal**: Cleans up extra spaces
- **End-of-file fixer**: Ensures files end with newlines

### Running Quality Checks

```bash
# Run all pre-commit hooks on all files
pre-commit run --all-files

# Run pre-commit hooks on staged files only
pre-commit run

# Run specific checks
mypy src/
ruff check src/
black src/ --check
pytest tests/

# Fix formatting issues
black src/
isort src/
ruff check --fix src/
```

### Quality Standards

All code must pass these checks:

1. **Type Safety**: MyPy must pass with no errors
2. **Code Style**: Black formatting must be applied
3. **Import Order**: isort must organize imports
4. **Linting**: Ruff must pass with no violations
5. **Security**: No secrets or API keys in code
6. **Tests**: Minimum 80% test coverage for new code

## 📋 Coding Standards

### Python Style Guide

We follow PEP 8 with these additions:

```python
# Good: Clear, typed, documented with NumPy-style docstrings
def assign_task(agent_id: str, task_id: str, priority: int = 1) -> TaskAssignment:
    """
    Assign a task to an agent with optional priority.

    Parameters
    ----------
    agent_id : str
        Unique identifier of the agent
    task_id : str
        Unique identifier of the task
    priority : int, optional
        Task priority (1-5), by default 1

    Returns
    -------
    TaskAssignment
        Assignment details including agent, task, and timestamp

    Raises
    ------
    AgentNotFoundError
        If agent doesn't exist
    TaskNotFoundError
        If task doesn't exist
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
2. **Docstrings**: Every public function/class needs a NumPy-style docstring
3. **Error Handling**: Use Marcus Error Framework for user-facing errors (see [CLAUDE.md](CLAUDE.md))
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
git commit -m "test(core): add tests for task dependency resolution"

# Bad examples
git commit -m "fixed stuff"
git commit -m "WIP"
git commit -m "updates"
```

## 🧪 Testing

### Test Organization

📖 **See:** [Test Writing Instructions in CLAUDE.md](CLAUDE.md#test-writing-instructions)

```
tests/
├── unit/                    # Fast, isolated unit tests
│   ├── ai/
│   ├── core/
│   ├── mcp/
│   └── visualization/
├── integration/             # Tests requiring external services
│   ├── e2e/
│   ├── api/
│   ├── external/
│   └── diagnostics/
├── future_features/         # TDD tests for unimplemented features
└── performance/             # Performance tests
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/core/test_task_manager.py

# Run specific test
pytest tests/unit/core/test_task_manager.py::test_assign_task

# Run only unit tests (fast)
pytest tests/unit/

# Run integration tests
pytest tests/integration/

# Skip slow tests
pytest -m "not slow"
```

### Writing Tests

Follow the Test-Driven Development (TDD) approach:

```python
# Good test example with NumPy-style docstring
def test_agent_registration_with_valid_data():
    """
    Test that agents can register with valid data.

    This test verifies the happy path for agent registration,
    ensuring all required fields are properly stored.
    """
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
    """Create a mock agent for testing."""
    return Agent(
        id="test-001",
        name="Test Agent",
        skills=["python", "testing"]
    )
```

## 📚 Documentation

### When to Update Docs

Update documentation when you:
- Add a new feature
- Change existing behavior
- Fix a confusing part of the docs
- Add a new example or tutorial

### Documentation Structure

📖 **See:** [docs/README.md](docs/README.md) for the complete structure

```
docs/source/
├── getting-started/     # New user guides and quickstart
├── guides/              # How-to guides for users
├── developer/           # Developer and contributor guides
│   ├── local-development.md
│   ├── development-workflow.md
│   └── configuration.md
├── concepts/            # High-level design and philosophy
├── systems/             # Technical architecture (53 systems)
├── api/                 # API reference
└── roadmap/             # Future plans
```

### Documentation Placement Rules

📖 **See:** [CLAUDE.md - DOCUMENTATION_PLACEMENT_RULES](CLAUDE.md#documentation-placement-rules)

1. **Determine audience FIRST:**
   - End users → `/docs/source/guides/`
   - Developers → `/docs/source/developer/`
   - Concepts → `/docs/source/concepts/`
   - Architecture → `/docs/source/systems/`

2. **Use descriptive filenames**: `setup-github-integration.md` not `github.md`

3. **Check if docs already exist**: Update rather than duplicate

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
   export MARCUS_KANBAN_PROVIDER=github
   export MARCUS_KANBAN_GITHUB_TOKEN=ghp_xxxxxxxxxxxx
   export MARCUS_KANBAN_GITHUB_OWNER=your_username
   export MARCUS_KANBAN_GITHUB_REPO=your_repo
   ```

3. **Verify Connection**
   ```bash
   docker compose restart marcus
   docker compose logs marcus
   ```

# Bad: Vague, unstructured
## GitHub Setup
You need a token and project URL. Set them in the environment.
```

## 🔍 Code Review Guidelines

Effective code review benefits both the reviewer and the author. Here's how to make the most of it:

### For Reviewers

**Review Priorities (in order):**

1. **Correctness**: Does the code solve the intended problem?
2. **Tests**: Are edge cases and error conditions covered?
3. **Clarity**: Is the code understandable to others?
4. **Performance**: Are there obvious inefficiencies?
5. **Security**: Any potential vulnerabilities?
6. **Compatibility**: Does it break existing functionality?

**Giving Constructive Feedback:**

✅ **Do:**
- Be respectful and constructive
- Explain the "why" behind suggestions
- Distinguish between "must fix" and "nice to have"
- Acknowledge good work and clever solutions
- Ask questions rather than making demands
- Provide examples or references when possible

❌ **Don't:**
- Make personal comments
- Be dismissive of different approaches
- Nitpick trivial style issues (we have pre-commit for that)
- Block PRs without clear rationale

**Example feedback:**

```markdown
# Good
"This could be more efficient using a dictionary lookup instead of a
list search. For large datasets, this would be O(1) vs O(n). See
example: [link]"

# Not helpful
"This is slow and wrong."
```

### For Authors

**Receiving Feedback:**

✅ **Do:**
- Assume good intentions from reviewers
- Ask for clarification if feedback is unclear
- Discuss disagreements professionally with technical reasoning
- Learn from suggestions and apply patterns to future work
- Thank reviewers for their time
- Update the PR promptly to address feedback

❌ **Don't:**
- Take feedback personally
- Ignore or dismiss comments without discussion
- Make changes without understanding why
- Get defensive about your approach

**Responding to Reviews:**

```markdown
# Good responses
"Great point! I've updated to use the dictionary approach. Much cleaner."
"I kept the list approach here because X, Y, Z. What do you think?"
"I'm not sure I understand this suggestion. Could you clarify?"

# Not helpful
"Whatever, I'll change it."
"This is fine."
```

### Review Etiquette

- **Response Time**: We aim to review PRs within 3-5 business days
- **Review Iterations**: Expect 1-3 rounds of feedback for most PRs
- **Stale PRs**: PRs without activity for 6 weeks may be closed (you can reopen later)
- **Breaking the Ice**: First-time contributors may need extra guidance - be patient and welcoming!

## 🔄 Pull Request Process

### Before Submitting

- [ ] All pre-commit hooks pass (`pre-commit run --all-files`)
- [ ] Tests pass locally (`pytest`)
- [ ] MyPy type checking passes (`mypy src/`)
- [ ] Code is formatted with Black (`black src/`)
- [ ] Imports are organized with isort (`isort src/`)
- [ ] Ruff linting passes (`ruff check src/`)
- [ ] No secrets detected (`detect-secrets scan`)
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

## Branch Information
- [ ] This PR targets the `develop` branch
- [ ] My branch is up-to-date with `upstream/develop`
- [ ] I'm working in my fork's feature branch

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed
- [ ] Test coverage is ≥80%

## Documentation
- [ ] Updated relevant docs
- [ ] Added docstrings to new code
- [ ] Updated CHANGELOG.md (if applicable)

## Checklist
- [ ] My code follows the style guide
- [ ] I've added tests for my changes
- [ ] All quality checks pass
```

### Review Process

1. **Automated Checks**: CI runs tests, linting, and security checks
2. **Code Review**: Maintainers review for quality and fit
3. **Feedback**: Address any requested changes
4. **Approval**: Once approved, we'll merge your PR!

### After Your PR is Merged

```bash
# 1. Delete your feature branch locally and remotely
git branch -d feature/your-feature-name
git push origin --delete feature/your-feature-name

# 2. Update your fork's develop branch
git checkout develop
git pull upstream develop
git push origin develop

# 3. Celebrate! You've contributed to Marcus! 🎉
```

## 🎯 Areas Needing Help

Looking for something to work on? These areas need attention:

### High Priority
- 🧪 **Test Coverage**: Especially integration tests
- 📚 **Documentation**: Tutorials and examples
- 🐛 **Bug Fixes**: Check the issue tracker
- 🔧 **Provider Support**: Add support for Jira, Trello, Linear

### Feature Ideas
- 📊 Better progress visualization
- 🔌 More MCP tool implementations
- 🌐 Internationalization support
- 📱 Mobile-friendly dashboard
- 🤖 More AI provider integrations

## 💬 Getting Help

### Where to Ask Questions

- **[GitHub Discussions](https://github.com/lwgray/marcus/discussions)**: For general questions and ideas
- **Issue Comments**: For specific issues
- **[Discord](https://discord.gg/marcus)**: Join our community

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

## 📖 Additional Resources

### Learn More About Marcus
- [Core Concepts](docs/source/getting-started/core-concepts.md)
- [Agent Workflow Guide](docs/source/guides/agent-workflows/agent-workflow.md)
- [Philosophy](docs/source/concepts/philosophy.md)
- [Systems Architecture](docs/source/systems/README.md)

### Developer Resources
- [Local Development Setup](docs/source/developer/local-development.md)
- [Development Workflow](docs/source/developer/development-workflow.md)
- [Configuration Reference](docs/source/developer/configuration.md)
- [CLAUDE.md](CLAUDE.md) - Project-specific development guidelines

### Improve Your Skills
- [Python Testing Guide](https://realpython.com/python-testing/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [How to Write Good Documentation](https://www.writethedocs.org/guide/)

### Tools We Use
- [Black](https://black.readthedocs.io/) - Code formatter
- [Pytest](https://docs.pytest.org/) - Testing framework
- [MyPy](https://mypy.readthedocs.io/) - Type checking
- [Pre-commit](https://pre-commit.com/) - Git hooks
- [Sphinx](https://www.sphinx-doc.org/) - Documentation

---

## Thank You!

Every contribution makes Marcus better. Whether it's your first open source contribution or your thousandth, we're grateful you're here.

Welcome to the Marcus community! 🚀
