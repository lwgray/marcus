# Documentation Placement Guide for AI Agents

## Quick Decision Tree

When creating documentation, ask yourself:

1. **Who is the primary audience?**
   - End users → `user-guide/`
   - Developers/Contributors → `developer-guide/`
   - DevOps/SysAdmins → `operations-guide/`
   - Internal team only → `archive/internal/`

2. **What type of content is it?**
   - How to use a feature → `user-guide/how-to/`
   - Conceptual explanation → `user-guide/concepts/`
   - API/Code documentation → `developer-guide/` or `developer-guide/sphinx/`
   - Deployment instructions → `operations-guide/`
   - Planning/Discussion → `archive/planning/`

## Prompt Templates for Agents

### For User Documentation

```
"Create a user guide for [FEATURE] that explains how to use it. 
Place it in docs/user-guide/how-to/[feature-name].md if it's a step-by-step guide,
or docs/user-guide/concepts/[feature-name].md if it's explaining concepts.
Include practical examples and avoid technical jargon."
```

### For Developer Documentation

```
"Create developer documentation for [COMPONENT/API] that explains how it works internally.
Place it in docs/developer-guide/[component-name].md for standalone docs,
or docs/developer-guide/sphinx/source/[appropriate-section]/ for detailed technical docs.
Include code examples, architecture decisions, and API references."
```

### For Operations Documentation

```
"Create deployment/operations documentation for [DEPLOYMENT-SCENARIO].
Place it in docs/operations-guide/setup/[platform-name].md for platform-specific guides,
or docs/operations-guide/[topic].md for general operations topics.
Include environment variables, configuration options, and troubleshooting steps."
```

## Decision Criteria

### Place in `user-guide/` when:
- Explaining how to use Marcus features
- Writing getting started guides
- Creating tutorials for end users
- Documenting commands or UI
- Writing troubleshooting guides for users

### Place in `developer-guide/` when:
- Documenting code architecture
- Explaining APIs or interfaces
- Writing contribution guidelines
- Creating technical deep-dives
- Documenting integration points

### Place in `operations-guide/` when:
- Writing deployment guides
- Documenting infrastructure setup
- Creating monitoring guides
- Explaining configuration options
- Writing scaling or performance guides

### Place in `archive/` when:
- Creating internal planning documents
- Writing meeting notes or discussions
- Documenting decisions not ready for public
- Creating experimental documentation

## File Naming Conventions

1. **Use descriptive names**: `setup-github-integration.md` not `github.md`
2. **Use kebab-case**: `my-new-feature.md` not `my_new_feature.md`
3. **Be specific**: `troubleshoot-task-creation-errors.md` not `errors.md`
4. **Include the type**: `how-to-configure-linear.md` not just `linear.md`

## Example Prompts That Work Well

### Good Prompt Example 1:
```
"Document the new task assignment algorithm. This is technical documentation 
for developers who want to understand how Marcus assigns tasks to agents. 
Include the algorithm logic, decision factors, and code examples.
Place it in developer-guide/ since it's for developers understanding internals."
```

### Good Prompt Example 2:
```
"Create a user guide for the new 'add_feature' natural language tool.
Show users how to use it with examples of good feature descriptions.
This should go in user-guide/how-to/ since it's teaching users how to use a feature.
Name it 'use-natural-language-features.md'."
```

### Good Prompt Example 3:
```
"Write a guide for deploying Marcus on AWS with ECS. Include all necessary
AWS services, environment setup, and configuration. This is for DevOps teams,
so place it in operations-guide/setup/deploy-aws-ecs.md"
```

## What to Include in Your Prompt

1. **Target Audience**: "for users", "for developers", "for DevOps"
2. **Document Type**: "how-to guide", "reference", "tutorial", "concept explanation"
3. **Specific Placement**: Suggest the directory if you know it
4. **Key Points**: What must be included
5. **Examples Needed**: Request specific examples if needed

## Red Flags - Wrong Placement

❌ User guides in `developer-guide/`
❌ API documentation in `user-guide/`
❌ Internal planning in `user-guide/` or `developer-guide/`
❌ Deployment guides in `developer-guide/` (should be in `operations-guide/`)
❌ Contributing guidelines in `user-guide/` (should be in `developer-guide/`)

## Quick Reference

| Content Type | Location | Example |
|-------------|----------|---------|
| How to use a feature | `user-guide/how-to/` | `use-github-integration.md` |
| Concept explanation | `user-guide/concepts/` | `understanding-task-states.md` |
| API documentation | `developer-guide/` | `api-endpoints.md` |
| Architecture | `developer-guide/sphinx/source/developer/` | `system-architecture.md` |
| Deployment | `operations-guide/` | `deploy-kubernetes.md` |
| Platform setup | `operations-guide/setup/` | `setup-linear.md` |
| Internal planning | `archive/planning/` | `q4-roadmap.md` |

## Template for Clear Documentation Requests

```
Please create [TYPE] documentation for [TOPIC].

Target audience: [users/developers/operators]
Purpose: [what the reader should learn/accomplish]
Include: [specific points to cover]
Examples: [what examples to include]
Place in: docs/[suggested-directory]/
Filename: [suggested-filename].md

Context: [why this documentation is needed]
```

---

Remember: When in doubt, check the README.md in each major directory for guidance on what belongs there!