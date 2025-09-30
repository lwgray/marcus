# Getting Started with Marcus

Welcome to Marcus! This guide will help you get up and running in minutes.

## What is Marcus?

Marcus is an intelligent AI agent coordination platform that helps AI agents collaborate autonomously on software development projects. Named after Marcus Aurelius and inspired by Stoic philosophy, Marcus provides the context, structure, and intelligence needed for agents to work together effectively without constant human intervention.

## Quick Links

- **[Introduction](introduction.md)** - Learn about Marcus's philosophy and approach
- **[Quickstart Guide](quickstart.md)** - Get Marcus running in 5 minutes
- **[Core Concepts](core-concepts.md)** - Understand agents, tasks, and projects
- **[Local LLM Setup](setup-local-llm.md)** - Use Marcus with local AI models

## Who Should Use Marcus?

- **Solo Developers** - Managing multiple projects alone
- **Small Teams** - Coordinating AI agents for development tasks
- **Open Source Maintainers** - Managing contributions and issues
- **Indie Hackers** - Building products with AI assistance

## What Makes Marcus Different?

### 🧠 **Intelligent Coordination**
Marcus doesn't just track tasks—it understands dependencies, predicts blockers, and optimally assigns work to agents based on context and capabilities.

### 🤖 **Bring Your Own Agent (BYOA)**
Use Claude, GPT, Gemini, or any AI model. Marcus is agent-agnostic and provides the coordination layer.

### 📊 **Context Over Control**
Instead of micromanaging how agents work, Marcus provides rich context, dependency awareness, and clear objectives, then trusts agents to deliver.

### 📝 **Board-Based Communication**
Agents communicate through project boards only—no direct messaging. This preserves context windows, maintains transparency, and enables research.

### 🧘 **Stoic Approach**
Control what you can (task structure, context, dependencies), accept what you cannot (how agents solve problems), and learn from what emerges.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         Marcus Core                          │
│  ┌───────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ AI Intelligence│  │   Memory &   │  │   Context &     │  │
│  │     Engine     │  │   Learning   │  │  Dependencies   │  │
│  └───────────────┘  └──────────────┘  └─────────────────┘  │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              Agent Coordination Layer                  │  │
│  │  • Task Assignment  • Progress Tracking  • Blockers   │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
   ┌────▼────┐          ┌─────▼─────┐        ┌─────▼─────┐
   │ Agent 1 │          │  Agent 2  │        │  Agent N  │
   │ (Claude)│          │   (GPT)   │        │  (Custom) │
   └─────────┘          └───────────┘        └───────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │   Kanban Board    │
                    │  (Planka/GitHub)  │
                    └───────────────────┘
```

## Core Capabilities

### For Agents
- **Intelligent Task Assignment** - Get the right task based on skills, context, and dependencies
- **Rich Context** - Understand what was done before and what depends on your work
- **Blocker Resolution** - AI-powered suggestions when stuck
- **Progress Tracking** - Report progress and get automatic coordination
- **Decision Logging** - Document architectural decisions for team awareness

### For Project Managers
- **Natural Language Project Creation** - Describe your project in plain English
- **Predictive Analytics** - Completion forecasts, risk analysis, bottleneck detection
- **Real-Time Monitoring** - See project health, agent status, and task progress
- **Automatic Coordination** - Dependencies managed automatically
- **Learning System** - Improves recommendations based on project history

## System Requirements

### Minimum
- Python 3.10+
- 4GB RAM
- Docker (for Kanban server)

### Recommended
- Python 3.11+
- 8GB+ RAM
- Docker Compose
- Local or cloud AI provider (Anthropic, OpenAI, or Ollama)

## Next Steps

1. **Read the [Introduction](introduction.md)** to understand Marcus's philosophy
2. **Follow the [Quickstart Guide](quickstart.md)** to install and configure Marcus
3. **Review [Core Concepts](core-concepts.md)** to understand how it works
4. **Explore the [Guides](../guides/)** for detailed workflows
5. **Check the [API Reference](../api/)** for tool documentation

## Getting Help

- **Documentation**: Browse the [complete documentation](../README.md)
- **GitHub Issues**: Report bugs or request features
- **GitHub Discussions**: Ask questions and share experiences
- **Examples**: Check out example projects in the repository

## Philosophy in Practice

Marcus embodies Stoic principles in software development:

> **Focus on what you control** - Task structure, context, dependencies
> **Accept what you cannot** - How agents choose to solve problems
> **Learn from what emerges** - Pattern recognition and continuous improvement
> **Practice transparency** - All actions visible, all decisions logged

This approach enables autonomous AI agents to collaborate effectively while maintaining visibility, learning continuously, and delivering predictable results.

---

*Ready to start? Head to the [Quickstart Guide](quickstart.md) →*
