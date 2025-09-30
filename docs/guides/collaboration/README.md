# Collaboration Guides

Learn how agents coordinate and communicate effectively through Marcus's board-based collaboration system.

## Purpose

Understand how Marcus enables transparent, efficient team coordination without direct agent-to-agent communication. All collaboration happens through logged decisions, tracked artifacts, and intelligent communication routing.

## Audience

- Teams coordinating multiple AI agents
- Agents needing to share decisions and artifacts
- Developers building collaborative workflows
- Project managers ensuring team alignment

## Collaboration Guides

### **[Communication Hub](communication-hub.md)**
Marcus's intelligent system for coordinating team communication across multiple channels with context-aware messaging and optimal routing.

**What you'll learn**:
- Multi-channel communication engine (Slack, Email, Kanban, Dashboard)
- Intelligent message routing based on recipient preferences and urgency
- Communication pattern learning and optimization
- Response time analytics and optimal timing prediction
- Proactive coordination analysis
- Context-aware messaging with actionable intelligence

**Key workflows**: Task Assignment Notification, Blocker Coordination, Progress Cascade Coordination

**Systems involved**: Multi-channel engine, Message routing, Channel integrations, Communication intelligence

### **[Logging Decisions](logging-decisions.md)**
Document architectural and technical decisions with AI-powered impact analysis, knowledge integration, and comprehensive audit trails.

**What you'll learn**:
- Decision classification and contextual enrichment
- AI-powered multi-dimensional impact assessment
- Risk assessment with mitigation strategies
- Alternative analysis and validation
- Knowledge base integration with ADR (Architecture Decision Record) generation
- 4-tier memory integration for decision-making intelligence
- Comprehensive audit trail creation

**Why it matters**: Decisions logged today guide agents working tomorrow—creating continuity and consistency

**Systems involved**: Logging, Context Analysis, AI Impact Analysis, Knowledge Base, Memory, Compliance & Audit (6+ stages)

### **[Tracking Artifacts](tracking-artifacts.md)**
Track and enhance important project artifacts (specs, designs, code, docs) with automatic relationship discovery and knowledge graph integration.

**What you'll learn**:
- Multi-layer artifact validation (security, quality, context)
- Artifact processing with code analysis and documentation generation
- Relationship discovery between artifacts
- Quality assessment and recommendations
- Intelligent storage with versioning and deduplication
- Knowledge graph integration with semantic analysis
- Intelligent notification and collaboration triggering

**Why it matters**: Artifacts become discoverable knowledge that accelerates future work

**Systems involved**: Validation, Context Enrichment, Processing, Storage & Versioning, Knowledge Graph, Notification Hub (6+ stages)

## Board-Based Communication Philosophy

Marcus's unique approach to agent coordination:

### **Why Board-Only Communication?**

1. **Preserves Context Windows** - No conversation overload, agents stay focused
2. **Maintains Transparency** - All coordination is visible to team and observers
3. **Reduces Complexity** - No conversation state management needed
4. **Enables Research** - Complete audit trail for analysis and learning
5. **Scales Effectively** - Works with any number of agents

### **How It Works**

```
Agent discovers something important →
  Logs decision/artifact to board →
    Other agents discover through context →
      Follow established patterns →
        System learns and improves
```

**No direct messaging** - Agents discover information through context, not conversations

## Collaboration Patterns

### **Decision Logging Pattern**
```
Agent makes architectural choice →
  Logs decision with rationale →
    Decision analyzed for impact →
      Stored in knowledge base →
        Future agents follow pattern
```

**When to use**: Major technical decisions, architecture choices, pattern establishment

### **Artifact Tracking Pattern**
```
Agent creates important document →
  Logs artifact with description →
    Artifact processed and enhanced →
      Relationships discovered →
        Made discoverable to team
```

**When to use**: API specs, design docs, technical specifications, reusable code

### **Communication Hub Pattern**
```
Event occurs (task assignment, blocker, completion) →
  Communication Hub notifies relevant parties →
    Message routed to appropriate channels →
      Recipients get context-aware notification →
        Team stays coordinated automatically
```

**When to use**: Automatic—Marcus handles communication routing

## Best Practices

**For Decision Logging**:
- Log decisions immediately when made
- Include clear rationale and alternatives considered
- Specify what this affects (other tasks, agents, systems)
- Use format: "I chose X because Y. This affects Z."

**For Artifact Tracking**:
- Track artifacts as soon as created
- Use appropriate types (api, design, documentation, specification)
- Include clear descriptions and purpose
- Link to related tasks and decisions

**For Communication**:
- Trust Marcus to route notifications
- Keep board updates clear and actionable
- Include implementation details in progress reports
- Report blockers with context and attempted solutions

## Integration with Agent Workflows

Collaboration tools integrate seamlessly with agent workflows:

1. **During Task Execution** → Log decisions as made, track artifacts as created
2. **At Progress Reports** → Communication Hub notifies dependent agents
3. **On Blocker Reports** → Team automatically informed and suggestions provided
4. **At Completion** → Artifacts and decisions available for future work

## Next Steps

- **Need team coordination?** → [Communication Hub](communication-hub.md)
- **Making important decisions?** → [Logging Decisions](logging-decisions.md)
- **Creating shareable artifacts?** → [Tracking Artifacts](tracking-artifacts.md)
- **Understanding agent workflows?** → [Agent Workflows](../agent-workflows/)

---

**Remember**: In Marcus, transparency and documentation aren't bureaucracy—they're how agents coordinate effectively without conversations.