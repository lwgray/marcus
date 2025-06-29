# Marcus Documentation Index

This file maps all documentation in the Marcus project and their purpose.

## Root Documentation Files

- `README.md` - Main project entry point (needs fixing - has broken links)
- `CONTRIBUTING.md` - Contribution guidelines
- `CLAUDE.md` - Claude agent instructions (project-specific)
- `CLAUDE.local.md` - Local Claude instructions (not in git)

## /docs Directory Structure

### 📋 Planning & Analysis
Located in `/docs/planning/`:
- `DOCUMENTATION_IMPROVEMENT_ACTION_PLAN.md` - Action plan for docs improvement
- `DOCUMENTATION_QUALITY_ANALYSIS.md` - Quality analysis of existing docs
- `MARCUS_UX_DOCUMENTATION_ANALYSIS.md` - UX documentation analysis
- `mcp_implementation_plan.md` - MCP implementation planning
- `mcp_tools_analysis.md` - Analysis of MCP tools
- `mcp_tools_plan.md` - Planning for MCP tools
- `missing_mcp_tools.md` - List of missing MCP tools
- `visualization_redesign_notes.md` - Notes on visualization redesign

### 🚀 Setup & Installation
Located in `/docs/setup/`:
- `docker_setup.md` - Docker setup instructions
- `local_setup.md` - Local development setup
- `installation.md` - General installation guide (duplicate in root)

### 📚 Concepts & Architecture
Located in `/docs/concepts/`:
- `kanban-provider-abstraction.md` - Kanban provider abstraction layer
- `mcp-protocol.md` - MCP protocol explanation
- `task-assignment-intelligence.md` - Task assignment algorithm
- `worker-agents.md` - Worker agent architecture

### 🔧 Technical Documentation
Located in `/docs/technical/`:
- `mcp_tools_overview.md` - Overview of MCP tools

### 📖 Reference Documentation
Located in `/docs/reference/`:
- `ai_analysis_engine_api.md` - AI analysis engine API
- `configuration_guide.md` - Configuration reference
- `data_models_api.md` - Data models API reference
- `environment_variables.md` - Environment variables reference
- `index.md` - Reference index
- `kanban_providers_api.md` - Kanban providers API
- `mcp_tools_api.md` - MCP tools API reference
- `system_architecture.md` - System architecture
- `workspace_isolation_api.md` - Workspace isolation API

### 📘 How-To Guides
Located in `/docs/how-to/`:
- `deploy-on-kubernetes.md` - Kubernetes deployment
- `deploy-with-docker.md` - Docker deployment
- `deploy-with-python.md` - Python deployment
- `index.md` - How-to index
- `security-best-practices.md` - Security best practices
- `troubleshoot-common-issues.md` - Troubleshooting guide

### 🎯 MCP Tools Documentation
Located in `/docs/mcp_tools/`:
- `marcus_mcp_tools_reference.md` - Marcus MCP tools reference
- `mcp_tools_quick_reference.md` - Quick reference
- `add_feature_mermaid_diagrams.md` - Feature diagrams
- `add_feature_simple_mermaid.md` - Simple mermaid diagrams
- `code_duplication_analysis.md` - Code duplication analysis
- `create_project_workflow.md` - Project creation workflow
- `refactoring_summary.md` - Refactoring summary
- Various `.mermaid` diagram files

### 📝 Templates
Located in `/docs/templates/`:
- `CONCEPT_TEMPLATE.md` - Concept documentation template
- `GETTING_STARTED_TEMPLATE.md` - Getting started template
- `HOWTO_TEMPLATE.md` - How-to guide template
- `PRD_TEMPLATE.md` - Product requirements document template
- `PRODUCT_SPEC_TEMPLATE.md` - Product specification template
- `REFERENCE_TEMPLATE.md` - Reference documentation template
- `TUTORIAL_TEMPLATE.md` - Tutorial template

### 👥 Community
Located in `/docs/community/`:
- `SHOWCASE_TEMPLATE.md` - Template for showcases
- `showcases/README.md` - Showcase index
- `showcases/open-source-migration.md` - Open source migration example
- `showcases/startup-mvp-builder.md` - Startup MVP builder example

### 🌟 New Project Documentation
Located in `/docs/new_project/`:
- `problem_statement.md` - Project problem statement
- `marcus_hybrid_approach.md` - Hybrid approach design
- `implementation_prompt.md` - Implementation prompts
- `phase1_foundation.md` - Phase 1 foundation
- `phase2_intelligence.md` - Phase 2 intelligence
- `phase3_refinement.md` - Phase 3 refinement
- `phase4_scale.md` - Phase 4 scaling
- `pm_features_documentation.md` - PM features documentation
- `KANBAN_INTEGRATION_ANALYSIS.md` - Kanban integration analysis

### 🤝 Contributing
Located in `/docs/contributing/`:
- `contribution-examples.md` - Examples of contributions

### 📚 Sphinx Documentation
Located in `/docs/sphinx/`:
- Complete Sphinx documentation structure
- Source files in `source/` with subdirectories for:
  - `api/` - API documentation
  - `developer/` - Developer guides
  - `reference/` - Reference material
  - `templates/` - Documentation templates
  - `tutorials/` - Tutorials
  - `user_guide/` - User guides

### 📋 Standalone Documentation Files in /docs
- `BOARD_QUALITY_EXAMPLES.md` - Board quality examples
- `BOARD_QUALITY_STANDARDS.md` - Board quality standards
- `COMPREHENSIVE_DOCUMENTATION_ASSESSMENT.md` - Documentation assessment
- `INTEGRATION_GUIDE.md` - Integration guide
- `NATURAL_LANGUAGE_AND_AI_FEATURES.md` - NLP and AI features
- `NAYSAYERS.md` - Response to naysayers
- `NLP_BOARD_INTEGRATION_SUMMARY.md` - NLP board integration
- `OVERSTANDING.md` - Overstanding concept
- `START_PM_AGENT.md` - PM Agent startup guide
- `TECHNICAL_DOCUMENTATION_ANALYSIS.md` - Technical doc analysis
- `add_feature_usage.md` - Feature usage guide

## Other Documentation Locations

### /experiments
- `README.md` - Experiments overview
- Various setup and guide files for experiments
- `prompts/` - Agent prompts

### /projects
- `README.md` - Projects overview
- Project-specific documentation

### /tests
- `README.md` - Tests overview
- `README_TESTS.md` - Testing documentation
- `REAL_TESTS_README.md` - Real tests documentation

### /src/mcp
- `README.md` - MCP server documentation

### /prompts
- `system_prompts.md` - System prompts documentation

## Issues Found

1. **Broken Links in README.md** - Most documentation links point to non-existent files
2. **Duplicate Files** - Some files exist in multiple locations
3. **Inconsistent Organization** - Mix of different documentation types in root /docs
4. **Missing Core Documentation** - Several files referenced in README don't exist
5. **Sphinx vs Markdown** - Two parallel documentation systems