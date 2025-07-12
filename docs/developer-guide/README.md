# Developer Guide

Welcome to the Marcus Developer Guide! This directory contains technical documentation for developers and contributors.

## 📚 Contents

### Core Documentation
- [**API Overview**](api.md) - API documentation and examples
- [**Integration Guide**](INTEGRATION_GUIDE.md) - How to integrate with Marcus
- [**Contributing**](contributing.md) - How to contribute to Marcus

### Technical Topics

#### 🏗️ Architecture & Design
- [**Three-Tier Architecture**](architecture/three-tier-architecture.md) - User/Marcus/Agent separation
- [**MCP Tools by Role**](reference/mcp-tools-by-role.md) - Tool permissions and usage
- **Sphinx Documentation**: [sphinx/source/developer/](sphinx/source/developer/)
  - [Architecture Overview](sphinx/source/developer/architecture.md)
  - [System Design](sphinx/source/developer/system_design.md)
  - API Documentation

#### 📋 Standards & Guidelines
- [**Board Quality Standards**](BOARD_QUALITY_STANDARDS.md) - Task board quality guidelines
- [**Board Quality Examples**](BOARD_QUALITY_EXAMPLES.md) - Good vs bad board examples

#### 🤖 AI & NLP Features
- [**Natural Language Features**](NATURAL_LANGUAGE_AND_AI_FEATURES.md) - AI capabilities
- [**NLP Board Integration**](NLP_BOARD_INTEGRATION_SUMMARY.md) - How NLP integrates
- [**Pattern Learning System**](pattern-learning-system.md) - Automatic pattern extraction and learning

#### 🛠️ MCP Tools
The [mcp_tools/](mcp_tools/) directory contains:
- [Quick Reference](mcp_tools/mcp_tools_quick_reference.md)
- [Workflow Diagrams](mcp_tools/workflow_diagrams/)
- Tool implementations
- Integration examples

#### 📁 Other Resources
- [**Technical Docs**](technical/) - Deep technical documentation
- [**Templates**](templates/) - Documentation and code templates
- [**Contributing Guides**](contributing/) - Detailed contribution guides

## 🧭 Navigation Guide

### By Task

**Understanding the System**
1. Start with [Three-Tier Architecture](architecture/three-tier-architecture.md)
2. Review [MCP Tools by Role](reference/mcp-tools-by-role.md)
3. Read the [API Overview](api.md)
4. Study [System Design](sphinx/source/developer/system_design.md)

**Contributing Code**
1. Read [Contributing Guide](contributing.md)
2. Check [Board Quality Standards](BOARD_QUALITY_STANDARDS.md)
3. Use appropriate [Templates](templates/)

**Building Integrations**
1. See [Integration Guide](INTEGRATION_GUIDE.md)
2. Review [MCP Tools](mcp_tools/mcp_tools_quick_reference.md)
3. Study [NLP Features](NATURAL_LANGUAGE_AND_AI_FEATURES.md)

## 📖 Sphinx Documentation

The [sphinx/](sphinx/) directory contains comprehensive technical documentation:

```
sphinx/
├── source/
│   ├── developer/       # Developer documentation
│   ├── api/            # API reference
│   ├── tutorials/      # Technical tutorials
│   └── reference/      # Technical reference
└── build/              # Built documentation
```

To build Sphinx docs:
```bash
cd sphinx
make html
```

## 🔍 Can't Find Something?

- Check the main [Documentation Hub](../README.md)
- Look in [User Guide](../user-guide/) for usage documentation
- See [Operations Guide](../operations-guide/) for deployment info

---

[← Back to Documentation Hub](../README.md)
