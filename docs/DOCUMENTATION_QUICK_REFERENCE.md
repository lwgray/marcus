# Documentation Quick Reference for AI Agents

## 🎯 Where to Place Documentation

### Simple Rules:
1. **For users** → `/docs/user-guide/`
2. **For developers** → `/docs/developer-guide/`
3. **For deployment** → `/docs/operations-guide/`
4. **Internal only** → `/docs/archive/`

## 📝 How to Prompt Agents

### Formula:
```
"Create [TYPE] documentation for [TOPIC] aimed at [AUDIENCE].
Place it in docs/[DIRECTORY]/[filename].md
Include [SPECIFIC REQUIREMENTS]."
```

### Examples:

**User Feature Documentation:**
```
"Create a how-to guide for using the task assignment feature.
This is for end users who want to understand how to assign tasks to agents.
Place it in docs/user-guide/how-to/assign-tasks-to-agents.md
Include step-by-step instructions with examples."
```

**Technical Documentation:**
```
"Document the TaskAssignment class and its methods.
This is for developers who need to understand the assignment system internals.
Place it in docs/developer-guide/task-assignment-architecture.md
Include class diagrams, method descriptions, and code examples."
```

**Deployment Documentation:**
```
"Create a deployment guide for running Marcus on Google Cloud Platform.
This is for DevOps engineers setting up production environments.
Place it in docs/operations-guide/setup/deploy-gcp.md
Include required services, configuration, and estimated costs."
```

## 🚦 Quick Decision Guide

Ask: **"Who needs this information?"**

| If they need to... | They are... | Put docs in... |
|-------------------|-------------|----------------|
| Use Marcus features | Users | `/user-guide/` |
| Understand how Marcus works conceptually | Users | `/user-guide/concepts/` |
| Follow step-by-step instructions | Users | `/user-guide/how-to/` |
| Write code or integrate | Developers | `/developer-guide/` |
| Understand architecture | Developers | `/developer-guide/sphinx/` |
| Deploy or operate Marcus | DevOps | `/operations-guide/` |
| Read internal discussions | Team only | `/archive/` |

## ✅ Good Practices

1. **Be specific** in your prompts:
   - ✅ "Create a troubleshooting guide for webhook connection errors"
   - ❌ "Document errors"

2. **Specify the audience**:
   - ✅ "for non-technical users"
   - ✅ "for developers familiar with Python"
   - ❌ "for people"

3. **Request examples**:
   - ✅ "Include 3 examples of valid task descriptions"
   - ✅ "Show code examples in Python and JavaScript"

4. **Suggest placement**:
   - ✅ "Place in docs/user-guide/how-to/"
   - ✅ "This belongs in developer documentation"

## 🔍 Finding Existing Documentation

Before creating new docs, check if it already exists:

```
"First, check if documentation already exists for [TOPIC] in:
- docs/user-guide/ (for user docs)
- docs/developer-guide/ (for technical docs)
- docs/developer-guide/sphinx/ (for detailed technical docs)

If it exists, update it. If not, create new documentation in [APPROPRIATE LOCATION]."
```

## 📋 Documentation Checklist

When requesting documentation, consider including:

- [ ] Target audience
- [ ] Prerequisites/required knowledge
- [ ] Step-by-step instructions (for how-tos)
- [ ] Code examples (for developer docs)
- [ ] Common errors and solutions
- [ ] Related documentation links
- [ ] Visual diagrams (if applicable)

---

**Remember**: Good documentation placement makes information easy to find. When in doubt, check `/docs/README.md` for the complete structure!