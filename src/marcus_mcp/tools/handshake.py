"""
Marcus MCP Handshake Tool

Provides agents with integration instructions and context
without requiring manual system prompt modifications.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class AgentType(Enum):
    """Supported agent types with different capabilities."""
    GENERAL = "general"
    BACKEND = "backend"
    FRONTEND = "frontend"
    FULLSTACK = "fullstack"
    DEVOPS = "devops"
    QA = "qa"
    REVIEWER = "reviewer"


class ContractVersion(Enum):
    """Contract version for backward compatibility."""
    V1_0 = "1.0"
    V1_1 = "1.1"
    V2_0 = "2.0"


@dataclass
class ToolContract:
    """Contract for individual tool usage."""
    name: str
    purpose: str
    required_fields: List[str]
    optional_fields: List[str] = field(default_factory=list)
    usage_pattern: str = ""
    examples: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowPhase:
    """Definition of a workflow phase."""
    name: str
    description: str
    required_tools: List[str]
    optional_tools: List[str] = field(default_factory=list)
    completion_criteria: str = ""
    next_phase: Optional[str] = None


@dataclass
class IntegrationContract:
    """Complete integration contract for Marcus agents."""
    
    # Contract metadata
    version: str = ContractVersion.V2_0.value
    agent_type: AgentType = AgentType.GENERAL
    timestamp: str = ""
    
    # Core constraints and capabilities
    constraints: List[str] = field(default_factory=list)
    capabilities: Dict[str, List[str]] = field(default_factory=dict)
    
    # Tool definitions and contracts
    tools: Dict[str, ToolContract] = field(default_factory=dict)
    
    # Workflow definition
    workflow_phases: List[WorkflowPhase] = field(default_factory=list)
    
    # Context injection instructions
    system_prompt_addition: str = ""
    behavioral_rules: List[str] = field(default_factory=list)
    
    # Git and development workflow
    git_workflow: Dict[str, str] = field(default_factory=dict)
    
    # Error handling and recovery
    error_patterns: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()
        
        if not self.constraints:
            self.constraints = [
                "You can ONLY use Marcus MCP tools provided in this contract",
                "You CANNOT ask for clarification - interpret tasks autonomously", 
                "You CANNOT choose tasks - accept what Marcus assigns",
                "You CANNOT communicate directly with other agents",
                "You MUST follow the workflow phases in sequence",
                "You MUST report progress at defined milestones"
            ]
        
        if not self.tools:
            self._initialize_tool_contracts()
        
        if not self.workflow_phases:
            self._initialize_workflow_phases()
        
        if not self.system_prompt_addition:
            self._initialize_system_prompt()
        
        if not self.behavioral_rules:
            self._initialize_behavioral_rules()
        
        if not self.git_workflow:
            self._initialize_git_workflow()
        
        if not self.error_patterns:
            self._initialize_error_patterns()
    
    def _initialize_tool_contracts(self):
        """Initialize tool contracts with detailed specifications."""
        self.tools = {
            "handshake": ToolContract(
                name="handshake",
                purpose="Get integration contract and instructions (call first)",
                required_fields=["agent_type"],
                optional_fields=["include_examples", "contract_version"],
                usage_pattern="Call once at startup before any other tools"
            ),
            "register_agent": ToolContract(
                name="register_agent", 
                purpose="Register yourself with Marcus system",
                required_fields=["agent_id", "name", "role"],
                optional_fields=["skills"],
                usage_pattern="Call once after handshake, before requesting tasks",
                examples={
                    "backend": {
                        "agent_id": "backend_dev_001",
                        "name": "Backend Developer", 
                        "role": "Backend Developer",
                        "skills": ["Python", "FastAPI", "PostgreSQL"]
                    }
                }
            ),
            "request_next_task": ToolContract(
                name="request_next_task",
                purpose="Get your next assigned task from Marcus",
                required_fields=["agent_id"],
                usage_pattern="Call when ready for work, after completing previous task"
            ),
            "report_task_progress": ToolContract(
                name="report_task_progress",
                purpose="Report progress on current task",
                required_fields=["agent_id", "task_id", "status"],
                optional_fields=["progress", "message"],
                usage_pattern="Report at 25%, 50%, 75%, 100% milestones with implementation details"
            ),
            "report_blocker": ToolContract(
                name="report_blocker",
                purpose="Report issues blocking task progress",
                required_fields=["agent_id", "task_id", "blocker_description"],
                optional_fields=["severity"],
                usage_pattern="Use when stuck - provides AI suggestions for resolution"
            ),
            "get_project_status": ToolContract(
                name="get_project_status",
                purpose="Check overall project status and metrics",
                required_fields=[],
                usage_pattern="Check periodically to understand project context"
            ),
            "get_agent_status": ToolContract(
                name="get_agent_status", 
                purpose="Check your current assignment and status",
                required_fields=["agent_id"],
                usage_pattern="Check if uncertain about current task assignment"
            )
        }
    
    def _initialize_workflow_phases(self):
        """Initialize workflow phases with clear progression."""
        self.workflow_phases = [
            WorkflowPhase(
                name="initialization",
                description="Agent startup and registration",
                required_tools=["handshake", "register_agent"],
                completion_criteria="Successfully registered with Marcus",
                next_phase="work_loop"
            ),
            WorkflowPhase(
                name="work_loop", 
                description="Continuous task execution cycle",
                required_tools=["request_next_task", "report_task_progress"],
                optional_tools=["report_blocker", "get_agent_status"],
                completion_criteria="Task marked as completed",
                next_phase="work_loop"  # Loops back to itself
            )
        ]
    
    def _initialize_system_prompt(self):
        """Initialize system prompt addition."""
        self.system_prompt_addition = f"""
## Marcus Integration Context (Auto-injected via MCP handshake)

You are an autonomous agent working through Marcus' MCP interface.
Contract Version: {self.version}
Agent Type: {self.agent_type.value}

INTEGRATION WORKFLOW:
1. Call handshake tool first to get this contract
2. Register yourself using register_agent  
3. Enter work loop: request_next_task → work → report_progress
4. Report progress at milestones with specific implementation details
5. Use report_blocker if stuck for AI assistance

CRITICAL CONSTRAINTS:
- Use ONLY the Marcus MCP tools defined in your contract
- Accept assigned tasks without asking for clarification
- Work autonomously and make reasonable assumptions
- Report progress with technical implementation details
- Follow git workflow patterns for your agent type

This context was automatically injected via MCP handshake - no manual configuration needed.
"""
    
    def _initialize_behavioral_rules(self):
        """Initialize behavioral rules."""
        self.behavioral_rules = [
            "Complete assigned tasks before requesting new ones",
            "Make reasonable assumptions when requirements are unclear",
            "Report implementation details in progress updates",
            "Use report_blocker for guidance when stuck",
            "Commit code regularly with descriptive messages",
            "Follow existing code patterns and conventions",
            "Include task IDs in commit messages for traceability"
        ]
    
    def _initialize_git_workflow(self):
        """Initialize git workflow based on agent type."""
        base_workflow = {
            "branch_strategy": "Work on assigned branch only",
            "commit_pattern": "feat(task-{id}): descriptive message with implementation details",
            "commit_frequency": "After logical units of work and before progress reports",
            "merge_policy": "Never merge or switch branches - stay on assigned branch"
        }
        
        if self.agent_type in [AgentType.BACKEND, AgentType.FRONTEND, AgentType.FULLSTACK]:
            base_workflow.update({
                "testing_requirement": "Run tests before final commit",
                "documentation": "Update relevant docs and API contracts in code"
            })
        
        self.git_workflow = base_workflow
    
    def _initialize_error_patterns(self):
        """Initialize error handling patterns."""
        self.error_patterns = {
            "dependency_missing": "Report blocker with specific missing dependency",
            "api_unavailable": "Work on parts that don't require the API, report blocker",
            "unclear_requirements": "Make reasonable assumptions, document in progress report",
            "test_failures": "Fix tests before reporting completion",
            "merge_conflicts": "Never attempt to resolve - report blocker immediately"
        }


async def handshake(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Provide agents with comprehensive Marcus integration contract.
    
    This tool implements the MCP protocol extension for agent handshake,
    returning a complete integration contract that eliminates the need
    for manual system prompt configuration.
    
    Args:
        arguments: Dict containing:
            - agent_type: Type of agent (backend, frontend, qa, etc.)
            - contract_version: Requested contract version (default: latest)
            - include_examples: Whether to include usage examples
            - capabilities: Agent's self-reported capabilities
    
    Returns:
        Dict containing complete integration contract and context
    """
    # Parse request parameters
    agent_type_str = arguments.get("agent_type", "general")
    contract_version = arguments.get("contract_version", ContractVersion.V2_0.value)
    include_examples = arguments.get("include_examples", True)
    agent_capabilities = arguments.get("capabilities", [])
    
    # Validate and convert agent type
    try:
        agent_type = AgentType(agent_type_str.lower())
    except ValueError:
        agent_type = AgentType.GENERAL
    
    # Create integration contract
    contract = IntegrationContract(
        version=contract_version,
        agent_type=agent_type
    )
    
    # Add agent-specific capabilities
    if agent_capabilities:
        contract.capabilities["declared"] = agent_capabilities
    
    # Build comprehensive response
    response = {
        "success": True,
        "contract": {
            "metadata": {
                "version": contract.version,
                "agent_type": contract.agent_type.value,
                "timestamp": contract.timestamp,
                "negotiated_capabilities": contract.capabilities
            },
            "constraints": contract.constraints,
            "tools": {
                name: {
                    "purpose": tool.purpose,
                    "required_fields": tool.required_fields,
                    "optional_fields": tool.optional_fields,
                    "usage_pattern": tool.usage_pattern,
                    "examples": tool.examples
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
            "error_handling": {
                "patterns": contract.error_patterns,
                "escalation": "Use report_blocker for AI assistance when stuck"
            }
        }
    }
    
    # Add examples if requested
    if include_examples:
        response["contract"]["examples"] = {
            "complete_workflow": {
                "1_handshake": {
                    "tool": "handshake",
                    "arguments": {"agent_type": agent_type.value}
                },
                "2_registration": {
                    "tool": "register_agent", 
                    "arguments": {
                        "agent_id": f"{agent_type.value}_agent_001",
                        "name": f"{agent_type.value.title()} Developer",
                        "role": f"{agent_type.value.title()} Developer",
                        "skills": _get_example_skills(agent_type)
                    }
                },
                "3_work_loop": [
                    {
                        "tool": "request_next_task",
                        "arguments": {"agent_id": f"{agent_type.value}_agent_001"}
                    },
                    {
                        "tool": "report_task_progress",
                        "arguments": {
                            "agent_id": f"{agent_type.value}_agent_001",
                            "task_id": "task_123",
                            "status": "in_progress", 
                            "progress": 50,
                            "message": "Implemented core functionality with tests"
                        }
                    }
                ]
            }
        }
    
    # Add integration instructions
    response["integration_instructions"] = {
        "immediate_actions": [
            "Add contract.context_injection.system_prompt_addition to your context",
            "Follow contract.workflow.phases in sequence",
            "Use only contract.tools for Marcus interactions"
        ],
        "contract_compliance": "This contract ensures standardized interaction patterns",
        "version_compatibility": f"Contract v{contract.version} - backward compatible with v1.x"
    }
    
    return response


def _get_example_skills(agent_type: AgentType) -> List[str]:
    """Get example skills for agent type."""
    skill_map = {
        AgentType.BACKEND: ["Python", "FastAPI", "PostgreSQL", "Redis"],
        AgentType.FRONTEND: ["React", "TypeScript", "CSS", "Webpack"],
        AgentType.FULLSTACK: ["Python", "React", "PostgreSQL", "TypeScript"],
        AgentType.DEVOPS: ["Docker", "Kubernetes", "AWS", "CI/CD"],
        AgentType.QA: ["Testing", "Selenium", "Jest", "Quality Assurance"],
        AgentType.REVIEWER: ["Code Review", "Architecture", "Security"],
        AgentType.GENERAL: ["Programming", "Problem Solving"]
    }
    return skill_map.get(agent_type, skill_map[AgentType.GENERAL])


# Tool definition for MCP registration  
HANDSHAKE_TOOL = {
    "name": "handshake",
    "description": "Get Marcus integration contract and context. Call this first for automatic setup!",
    "inputSchema": {
        "type": "object",
        "properties": {
            "agent_type": {
                "type": "string",
                "description": "Type of agent (backend, frontend, fullstack, devops, qa, reviewer, general)",
                "enum": [t.value for t in AgentType],
                "default": "general"
            },
            "contract_version": {
                "type": "string", 
                "description": "Requested contract version",
                "enum": [v.value for v in ContractVersion],
                "default": ContractVersion.V2_0.value
            },
            "include_examples": {
                "type": "boolean",
                "description": "Include usage examples and workflow demonstrations",
                "default": True
            },
            "capabilities": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Agent's self-reported capabilities for contract customization",
                "default": []
            }
        }
    }
}