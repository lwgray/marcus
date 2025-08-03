"""
Infrastructure and setup related cards for the Todo App.

This module contains card definitions for:
- Project setup and configuration
- Database connection and management
- Deployment and CI/CD
"""

INFRASTRUCTURE_CARDS = {
    "card-001": {
        "description": """## Overview
Set up the foundational project structure for the Todo App with proper organization and configuration.

## Objectives
- Create a scalable folder structure
- Set up development environment
- Configure build tools and dependencies
- Establish coding standards

## Technical Requirements

### Project Structure
```
todo-app/
├── backend/
│   ├── src/
│   │   ├── controllers/
│   │   ├── models/
│   │   ├── services/
│   │   ├── middleware/
│   │   ├── utils/
│   │   └── config/
│   ├── tests/
│   ├── package.json
│   └── tsconfig.json
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── hooks/
│   │   ├── utils/
│   │   └── styles/
│   ├── public/
│   ├── package.json
│   └── tsconfig.json
├── database/
│   ├── migrations/
│   └── seeds/
├── docs/
├── scripts/
└── docker-compose.yml
```

### Configuration Files
- **package.json**: Dependencies and scripts
- **tsconfig.json**: TypeScript configuration
- **.env.example**: Environment variables template
- **.gitignore**: Version control exclusions
- **.eslintrc**: Code style rules
- **prettier.config.js**: Code formatting

### Development Tools
- Node.js v18+
- TypeScript 5+
- ESLint & Prettier
- Docker & Docker Compose
- Git hooks (Husky)

## Success Criteria
- Clean project structure created
- All configuration files in place
- Development environment runs smoothly
- Code quality tools configured
- Documentation structure established""",
        "subtasks": [
            "Initialize Git repository",
            "Create folder structure",
            "Set up backend with Node.js and TypeScript",
            "Set up frontend with React and TypeScript",
            "Configure ESLint and Prettier",
            "Create Docker configuration",
            "Set up environment variables",
            "Configure build scripts",
            "Set up Git hooks with Husky",
            "Create initial README documentation",
        ],
        "labels": ["Infrastructure", "DevOps", "High Priority"],
        "priority": "high",
        "timeEstimate": 16,
    },
}

# Note: card-004 and card-017 would be added here as well
# Keeping this concise for demonstration