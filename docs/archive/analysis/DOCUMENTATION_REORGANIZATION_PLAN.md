# Marcus Documentation Reorganization Plan

## Current State Issues

1. **Broken README.md Links** - Points to non-existent files:
   - `docs/getting-started.md` (doesn't exist)
   - `docs/how-it-works.md` (doesn't exist)
   - `docs/commands.md` (doesn't exist)
   - `docs/deployment.md` (doesn't exist)
   - `docs/architecture.md` (exists in sphinx/source/developer/)
   - `docs/api.md` (doesn't exist)
   - `docs/faq.md` (exists in sphinx/source/reference/)

2. **Scattered Documentation** - Docs spread across multiple locations
3. **Duplicate Content** - Same information in different files
4. **No Clear Entry Point** - Users don't know where to start

## Proposed Organization

### Phase 1: Create Missing Core Documentation

Create these essential files referenced in README:
1. `/docs/getting-started.md` - First-time user guide
2. `/docs/how-it-works.md` - Simple explanation of Marcus
3. `/docs/commands.md` - Common commands reference
4. `/docs/deployment.md` - Deployment options guide
5. `/docs/api.md` - API overview (link to detailed references)
6. `/docs/faq.md` - Move from sphinx location

### Phase 2: Reorganize /docs Structure

```
/docs/
├── README.md                    # Documentation guide & index
├── getting-started.md          # NEW: First-time user guide
├── how-it-works.md            # NEW: Simple explanation
│
├── user-guide/                # End-user documentation
│   ├── installation.md        # Move from /docs/
│   ├── configuration.md       # Move from reference/
│   ├── commands.md           # NEW: Common commands
│   ├── providers.md          # Move from sphinx
│   ├── troubleshooting.md    # Move from how-to/
│   └── faq.md               # Move from sphinx
│
├── tutorials/               # Step-by-step guides
│   ├── quickstart.md       # NEW: 5-minute quickstart
│   ├── first-project.md    # NEW: First project tutorial
│   └── [existing tutorials from sphinx]
│
├── concepts/               # Conceptual documentation (keep as-is)
│   └── [existing files]
│
├── reference/              # Technical references (keep as-is)
│   └── [existing files]
│
├── developer/              # Developer documentation
│   ├── architecture.md     # Move from sphinx
│   ├── contributing.md     # Link to root CONTRIBUTING.md
│   ├── api/               # Detailed API docs
│   └── [other dev docs]
│
├── deployment/            # Deployment guides
│   ├── overview.md       # NEW: Deployment options
│   ├── docker.md         # Move from how-to/
│   ├── kubernetes.md     # Move from how-to/
│   └── python.md         # Move from how-to/
│
├── community/             # Keep as-is
├── templates/             # Keep as-is
├── planning/              # Keep as-is (internal docs)
└── archives/              # NEW: Old/deprecated docs
```

### Phase 3: Update README.md

Fix all broken links to point to actual files in the new structure.

### Phase 4: Create Documentation Hub

Create `/docs/README.md` as the main documentation index with:
- Clear navigation structure
- Purpose of each section
- Reading order for new users
- Search functionality notes

### Phase 5: Consolidate Duplicate Content

1. Merge Sphinx and Markdown documentation
2. Remove duplicate installation guides
3. Consolidate tutorial content
4. Single source of truth for each topic

## Implementation Order

1. **Immediate Fix** - Update README.md links to existing files
2. **Create Core Docs** - Write missing essential documentation
3. **Reorganize Structure** - Move files to new locations
4. **Update References** - Fix all internal links
5. **Archive Old Content** - Move deprecated docs to archives

## Success Criteria

- [ ] README.md has no broken links
- [ ] New users can get started in < 5 minutes
- [ ] Clear path from beginner to advanced
- [ ] No duplicate documentation
- [ ] All documentation is discoverable
- [ ] Consistent formatting and style