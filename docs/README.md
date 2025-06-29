# Marcus Documentation

Welcome to the Marcus documentation! All documentation is now organized into clear categories.

## 📁 Documentation Structure

```
docs/
├── README.md                    # This file - Documentation hub
├── user-guide/                  # For users of Marcus
│   ├── README.md               # User guide navigation
│   ├── getting-started.md       # Quick start guide
│   ├── installation.md          # Detailed installation
│   ├── how-it-works.md         # Conceptual overview
│   ├── commands.md             # Command reference
│   ├── add_feature_usage.md    # Using the add_feature tool
│   ├── START_PM_AGENT.md       # Starting PM Agent
│   ├── troubleshooting.md      # Common issues
│   ├── concepts/               # Conceptual documentation
│   ├── reference/              # Configuration & settings
│   ├── how-to/                # Step-by-step guides
│   └── community/              # Community examples
│
├── developer-guide/            # For developers & contributors
│   ├── README.md              # Developer guide navigation
│   ├── api.md                  # API overview
│   ├── contributing.md         # How to contribute
│   ├── INTEGRATION_GUIDE.md    # Integration guide
│   ├── BOARD_QUALITY_*.md      # Board quality standards
│   ├── NATURAL_LANGUAGE_*.md   # NLP features
│   ├── technical/              # Technical architecture
│   ├── templates/              # Documentation templates
│   ├── mcp_tools/             # MCP tools documentation
│   ├── contributing/          # Contribution guides
│   └── sphinx/                # 📖 SPHINX DOCS HERE! Technical documentation
│
├── operations-guide/          # For deployment & operations
│   ├── README.md             # Operations guide navigation
│   ├── deployment.md          # Deployment options
│   ├── monitoring.md          # Monitoring guide
│   └── setup/                # Setup guides
│
└── archive/                   # Internal & historical docs
    ├── analysis/             # Documentation analyses
    ├── planning/            # Planning documents
    └── internal/           # Internal notes

```

## 🎯 Quick Navigation

### I want to...

**Get Started**
- [Getting Started Guide](user-guide/getting-started.md) - 5 minute quickstart
- [Installation Guide](user-guide/installation.md) - Detailed setup
- [How It Works](user-guide/how-it-works.md) - Understand Marcus

**Use Marcus**
- [Commands Reference](user-guide/commands.md) - All commands
- [Configuration Guide](user-guide/reference/configuration_guide.md) - Settings
- [Troubleshooting](user-guide/troubleshooting.md) - Fix issues

**Develop with Marcus**
- [API Overview](developer-guide/api.md) - API documentation
- [Architecture](developer-guide/sphinx/source/developer/architecture.md) - System design
- [MCP Tools](developer-guide/mcp_tools/mcp_tools_quick_reference.md) - Tool reference

**Deploy Marcus**
- [Deployment Guide](operations-guide/deployment.md) - Deployment options
- [Setup Guides](operations-guide/setup/) - Provider-specific setup

## 📚 Documentation by Role

### 👤 **For Users**
Start with the [user-guide/](user-guide/) directory. This contains everything you need to use Marcus effectively.

### 👨‍💻 **For Developers**
Check out the [developer-guide/](developer-guide/) directory for API documentation, architecture details, and contribution guidelines.

### 🔧 **For Operators**
The [operations-guide/](operations-guide/) directory has deployment and monitoring information.

## 📖 About Sphinx Documentation

The Sphinx documentation is located at: **`developer-guide/sphinx/`**

Sphinx contains comprehensive technical documentation including:
- Detailed API documentation
- System architecture diagrams
- Developer tutorials
- Technical reference materials

To build and view Sphinx docs:
```bash
cd docs/developer-guide/sphinx
make html
open build/html/index.html  # Or browse to this file
```

## 🔍 Finding Information

1. **Use the directory structure** - Documentation is organized by role and purpose
2. **Check the README files** - Each major directory has its own README with navigation help
3. **Search within directories** - Related content is grouped together
4. **Follow cross-references** - Documents link to related topics
5. **For technical details** - Check the Sphinx documentation in `developer-guide/sphinx/`

## 📝 Documentation Standards

- User documentation uses simple language and examples
- Developer documentation includes technical details and code samples
- All documentation includes clear headings and navigation
- Examples are provided wherever possible

## 🚧 Documentation Status

This documentation was reorganized on 2025-06-29 to improve clarity and discoverability. If you find any broken links or missing content, please report it.

---

For questions or improvements, see [Contributing](developer-guide/contributing.md).