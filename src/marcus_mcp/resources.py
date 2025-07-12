"""
Marcus MCP Resources

Implements MCP resource discovery for contracts, schemas, and documentation.
This extends the standard MCP protocol to provide discoverable integration patterns.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import json

import mcp.types as types

from .tools.handshake import (
    IntegrationContract, 
    AgentType, 
    ContractVersion,
    _get_example_skills
)


class ContractResourceManager:
    """Manages MCP resources for integration contracts."""
    
    def __init__(self):
        self.base_uri = "marcus://contracts"
        self.schema_uri = "marcus://schemas"
        self.docs_uri = "marcus://docs"
    
    def list_resources(self) -> List[types.Resource]:
        """List all available MCP resources."""
        resources = []
        
        # Contract resources for each agent type
        for agent_type in AgentType:
            resources.append(
                types.Resource(
                    uri=f"{self.base_uri}/agent/{agent_type.value}",
                    name=f"{agent_type.value.title()} Agent Contract",
                    description=f"Integration contract for {agent_type.value} agents",
                    mimeType="application/json"
                )
            )
        
        # Schema resources
        resources.extend([
            types.Resource(
                uri=f"{self.schema_uri}/contract",
                name="Contract Schema",
                description="JSON schema for integration contracts",
                mimeType="application/json"
            ),
            types.Resource(
                uri=f"{self.schema_uri}/workflow",
                name="Workflow Schema", 
                description="JSON schema for workflow definitions",
                mimeType="application/json"
            ),
            types.Resource(
                uri=f"{self.schema_uri}/tool-usage",
                name="Tool Usage Schema",
                description="JSON schema for tool usage patterns",
                mimeType="application/json"
            )
        ])
        
        # Documentation resources
        resources.extend([
            types.Resource(
                uri=f"{self.docs_uri}/integration-guide",
                name="Agent Integration Guide",
                description="Complete guide for agent integration with Marcus",
                mimeType="text/markdown"
            ),
            types.Resource(
                uri=f"{self.docs_uri}/workflow-patterns",
                name="Workflow Patterns",
                description="Common workflow patterns and best practices",
                mimeType="text/markdown"
            ),
            types.Resource(
                uri=f"{self.docs_uri}/error-handling",
                name="Error Handling Guide",
                description="Error handling patterns and recovery strategies",
                mimeType="text/markdown"
            )
        ])
        
        return resources
    
    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read a specific resource by URI."""
        if uri.startswith(f"{self.base_uri}/agent/"):
            # Contract resource
            agent_type_str = uri.split("/")[-1]
            try:
                agent_type = AgentType(agent_type_str)
                return await self._get_agent_contract(agent_type)
            except ValueError:
                raise ValueError(f"Unknown agent type: {agent_type_str}")
        
        elif uri.startswith(f"{self.schema_uri}/"):
            # Schema resource
            schema_type = uri.split("/")[-1]
            return await self._get_schema(schema_type)
        
        elif uri.startswith(f"{self.docs_uri}/"):
            # Documentation resource
            doc_type = uri.split("/")[-1]
            return await self._get_documentation(doc_type)
        
        else:
            raise ValueError(f"Unknown resource URI: {uri}")
    
    async def _get_agent_contract(self, agent_type: AgentType) -> Dict[str, Any]:
        """Get integration contract for specific agent type."""
        contract = IntegrationContract(
            version=ContractVersion.V2_0.value,
            agent_type=agent_type
        )
        
        # Convert to dictionary format
        return {
            "contract_uri": f"{self.base_uri}/agent/{agent_type.value}",
            "metadata": {
                "version": contract.version,
                "agent_type": contract.agent_type.value,
                "timestamp": contract.timestamp,
                "generated_for": "MCP resource discovery"
            },
            "contract": {
                "constraints": contract.constraints,
                "tools": {
                    name: {
                        "purpose": tool.purpose,
                        "required_fields": tool.required_fields,
                        "optional_fields": tool.optional_fields,
                        "usage_pattern": tool.usage_pattern
                    }
                    for name, tool in contract.tools.items()
                },
                "workflow": {
                    "phases": [
                        {
                            "name": phase.name,
                            "description": phase.description,
                            "required_tools": phase.required_tools,
                            "optional_tools": phase.optional_tools,
                            "completion_criteria": phase.completion_criteria,
                            "next_phase": phase.next_phase
                        }
                        for phase in contract.workflow_phases
                    ]
                },
                "context_injection": {
                    "system_prompt_addition": contract.system_prompt_addition,
                    "behavioral_rules": contract.behavioral_rules
                },
                "git_workflow": contract.git_workflow,
                "error_handling": contract.error_patterns
            },
            "usage": {
                "integration_method": "Call handshake tool with agent_type parameter",
                "example_call": {
                    "tool": "handshake",
                    "arguments": {
                        "agent_type": agent_type.value,
                        "include_examples": True
                    }
                }
            }
        }
    
    async def _get_schema(self, schema_type: str) -> Dict[str, Any]:
        """Get JSON schema for various contract components."""
        schemas = {
            "contract": {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "title": "Marcus Integration Contract",
                "type": "object",
                "properties": {
                    "version": {"type": "string", "enum": [v.value for v in ContractVersion]},
                    "agent_type": {"type": "string", "enum": [t.value for t in AgentType]},
                    "timestamp": {"type": "string", "format": "date-time"},
                    "constraints": {"type": "array", "items": {"type": "string"}},
                    "tools": {"type": "object"},
                    "workflow_phases": {"type": "array"},
                    "system_prompt_addition": {"type": "string"},
                    "behavioral_rules": {"type": "array", "items": {"type": "string"}},
                    "git_workflow": {"type": "object"},
                    "error_patterns": {"type": "object"}
                },
                "required": ["version", "agent_type", "constraints", "tools", "workflow_phases"]
            },
            "workflow": {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "title": "Workflow Phase Definition",
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "required_tools": {"type": "array", "items": {"type": "string"}},
                    "optional_tools": {"type": "array", "items": {"type": "string"}},
                    "completion_criteria": {"type": "string"},
                    "next_phase": {"type": ["string", "null"]}
                },
                "required": ["name", "description", "required_tools"]
            },
            "tool-usage": {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "title": "Tool Usage Pattern",
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "purpose": {"type": "string"},
                    "required_fields": {"type": "array", "items": {"type": "string"}},
                    "optional_fields": {"type": "array", "items": {"type": "string"}},
                    "usage_pattern": {"type": "string"},
                    "examples": {"type": "object"}
                },
                "required": ["name", "purpose", "required_fields"]
            }
        }
        
        if schema_type not in schemas:
            raise ValueError(f"Unknown schema type: {schema_type}")
        
        return schemas[schema_type]
    
    async def _get_documentation(self, doc_type: str) -> str:
        """Get documentation in markdown format."""
        docs = {
            "integration-guide": """# Marcus Agent Integration Guide

## Overview
Marcus uses an MCP-based handshake system for automatic agent integration.

## Quick Start
1. Call `handshake` tool with your agent type
2. Add returned contract to your context
3. Follow the workflow phases provided

## Agent Types
- **backend**: Python/API development
- **frontend**: UI/React development  
- **fullstack**: Full application development
- **devops**: Infrastructure and deployment
- **qa**: Testing and quality assurance
- **reviewer**: Code review and architecture
- **general**: General purpose development

## Integration Flow
```
Agent Startup → handshake() → register_agent() → work_loop()
```

## Contract Compliance
- Use ONLY tools specified in your contract
- Follow workflow phases in sequence
- Report progress at defined milestones
- Use report_blocker when stuck

## Context Injection
The handshake contract includes a `system_prompt_addition` that should be added to your context for automatic compliance.
""",
            
            "workflow-patterns": """# Marcus Workflow Patterns

## Standard Agent Lifecycle

### 1. Initialization Phase
**Required Tools**: handshake, register_agent
**Pattern**: Get contract → Register with Marcus
**Completion**: Successfully registered

### 2. Work Loop Phase  
**Required Tools**: request_next_task, report_task_progress
**Optional Tools**: report_blocker, get_agent_status
**Pattern**: Request → Work → Report → Complete
**Completion**: Task marked completed

## Progress Reporting Pattern
Report at these milestones:
- 25%: Initial implementation started
- 50%: Core functionality complete
- 75%: Testing and refinement
- 100%: Task fully complete

## Error Handling Pattern
1. Try alternative approaches
2. Use report_blocker with specific details
3. Implement AI suggestions
4. Continue with unblocked portions

## Git Workflow Pattern
- Work on assigned branch only
- Commit with task ID: `feat(task-123): description`
- Push regularly for progress tracking
- Never merge - let Marcus handle integration
""",
            
            "error-handling": """# Marcus Error Handling Guide

## Standard Error Patterns

### Dependency Missing
```
Pattern: report_blocker with specific dependency
Action: Work on independent components
Recovery: Wait for dependency resolution
```

### API Unavailable
```
Pattern: Implement offline-capable portions
Action: Mock interfaces for testing
Recovery: Integrate when API available
```

### Unclear Requirements  
```
Pattern: Make reasonable assumptions
Action: Document assumptions in progress report
Recovery: Refine based on feedback
```

### Test Failures
```
Pattern: Fix before reporting completion
Action: Debug and resolve issues
Recovery: Never mark complete with failing tests
```

### Merge Conflicts
```
Pattern: NEVER attempt manual resolution
Action: Report blocker immediately  
Recovery: Let Marcus coordinate resolution
```

## Escalation Process
1. Attempt self-resolution for 15 minutes
2. Report blocker with attempted solutions
3. Implement AI suggestions
4. Work on unblocked portions
5. Re-evaluate periodically

## Recovery Strategies
- Graceful degradation when services unavailable
- Modular implementation to isolate issues
- Comprehensive error logging
- Clear communication of blockers
"""
        }
        
        if doc_type not in docs:
            raise ValueError(f"Unknown documentation type: {doc_type}")
        
        return docs[doc_type]


# Global resource manager instance
resource_manager = ContractResourceManager()


async def list_mcp_resources() -> List[types.Resource]:
    """List all available MCP resources for contract discovery."""
    return resource_manager.list_resources()


async def read_mcp_resource(uri: str) -> Dict[str, Any] | str:
    """Read a specific MCP resource by URI.""" 
    return await resource_manager.read_resource(uri)