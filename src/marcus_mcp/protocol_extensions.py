"""
Marcus MCP Protocol Extensions

Extends the standard MCP protocol with custom message types for:
- Capability negotiation
- Contract versioning
- Dynamic context updates
- Multi-step handshake processes
"""

from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json

import mcp.types as types

from .tools.handshake import AgentType, ContractVersion, IntegrationContract


class ProtocolMessageType(Enum):
    """Custom Marcus protocol message types."""
    ANNOUNCE = "marcus/announce"
    CONTRACT_OFFER = "marcus/contract_offer"
    CONTRACT_ACCEPT = "marcus/contract_accept"
    CONTRACT_REJECT = "marcus/contract_reject"
    CAPABILITY_UPDATE = "marcus/capability_update"
    CONTEXT_INJECTION = "marcus/context_injection"


@dataclass
class AgentAnnouncement:
    """Agent capability announcement message."""
    agent_id: str
    agent_type: AgentType
    version: str
    capabilities: List[str]
    preferred_contract_version: str = ContractVersion.V2_0.value
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()


@dataclass 
class ContractOffer:
    """Marcus contract offer to agent."""
    contract_id: str
    contract_version: str
    agent_type: AgentType
    contract: IntegrationContract
    negotiable_terms: List[str] = field(default_factory=list)
    expiry: str = ""
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()
        if not self.expiry:
            # Contracts expire in 1 hour by default
            from datetime import timedelta
            expiry_time = datetime.utcnow() + timedelta(hours=1)
            self.expiry = expiry_time.isoformat()


@dataclass
class ContractResponse:
    """Agent response to contract offer."""
    contract_id: str
    accepted: bool
    agent_id: str
    requested_modifications: List[Dict[str, Any]] = field(default_factory=list)
    reason: str = ""
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()


@dataclass
class CapabilityUpdate:
    """Runtime capability update message."""
    agent_id: str
    added_capabilities: List[str] = field(default_factory=list)
    removed_capabilities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()


@dataclass
class ContextInjection:
    """Dynamic context injection message."""
    agent_id: str
    context_type: str  # "system_prompt", "behavioral_rules", "constraints"
    context_data: Dict[str, Any]
    action: str = "add"  # "add", "remove", "replace"
    priority: str = "normal"  # "low", "normal", "high", "critical"
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()


class ProtocolExtensionHandler:
    """Handles Marcus protocol extensions."""
    
    def __init__(self):
        self.active_negotiations: Dict[str, ContractOffer] = {}
        self.agent_contracts: Dict[str, IntegrationContract] = {}
        self.agent_capabilities: Dict[str, List[str]] = {}
    
    async def handle_agent_announcement(
        self, announcement: AgentAnnouncement
    ) -> ContractOffer:
        """Handle agent capability announcement and respond with contract offer."""
        
        # Create tailored contract for this agent
        contract = IntegrationContract(
            version=announcement.preferred_contract_version,
            agent_type=announcement.agent_type
        )
        
        # Customize based on announced capabilities
        if announcement.capabilities:
            contract.capabilities["declared"] = announcement.capabilities
            
            # Add capability-specific customizations
            if "async" in announcement.capabilities:
                contract.behavioral_rules.append("Use async patterns for I/O operations")
            if "testing" in announcement.capabilities:
                contract.behavioral_rules.append("Write comprehensive tests before implementation")
            if "security" in announcement.capabilities:
                contract.behavioral_rules.append("Follow security best practices")
        
        # Create contract offer
        offer = ContractOffer(
            contract_id=f"contract_{announcement.agent_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            contract_version=contract.version,
            agent_type=announcement.agent_type,
            contract=contract,
            negotiable_terms=["tools", "workflow_phases", "git_workflow"]
        )
        
        # Store for tracking
        self.active_negotiations[offer.contract_id] = offer
        
        return offer
    
    async def handle_contract_response(
        self, response: ContractResponse
    ) -> Dict[str, Any]:
        """Handle agent response to contract offer."""
        
        if response.contract_id not in self.active_negotiations:
            raise ValueError(f"Unknown contract ID: {response.contract_id}")
        
        offer = self.active_negotiations[response.contract_id]
        
        if response.accepted:
            # Store accepted contract
            self.agent_contracts[response.agent_id] = offer.contract
            
            # Clean up negotiation
            del self.active_negotiations[response.contract_id]
            
            return {
                "success": True,
                "message": "Contract accepted and activated",
                "contract_id": response.contract_id,
                "agent_id": response.agent_id,
                "active_since": datetime.utcnow().isoformat()
            }
        
        else:
            # Handle rejection or modification requests
            if response.requested_modifications:
                # Attempt to accommodate modifications
                modified_contract = await self._apply_modifications(
                    offer.contract, 
                    response.requested_modifications
                )
                
                if modified_contract:
                    # Create new offer with modifications
                    new_offer = ContractOffer(
                        contract_id=f"contract_{response.agent_id}_mod_{datetime.utcnow().strftime('%H%M%S')}",
                        contract_version=modified_contract.version,
                        agent_type=modified_contract.agent_type,
                        contract=modified_contract
                    )
                    
                    self.active_negotiations[new_offer.contract_id] = new_offer
                    
                    return {
                        "success": True,
                        "message": "Modified contract offered",
                        "new_contract_id": new_offer.contract_id,
                        "modifications_applied": response.requested_modifications
                    }
            
            # Clean up failed negotiation
            del self.active_negotiations[response.contract_id]
            
            return {
                "success": False,
                "message": f"Contract rejected: {response.reason}",
                "contract_id": response.contract_id
            }
    
    async def handle_capability_update(
        self, update: CapabilityUpdate
    ) -> Dict[str, Any]:
        """Handle runtime capability updates."""
        
        if update.agent_id not in self.agent_capabilities:
            self.agent_capabilities[update.agent_id] = []
        
        current_caps = self.agent_capabilities[update.agent_id]
        
        # Apply capability changes
        for cap in update.added_capabilities:
            if cap not in current_caps:
                current_caps.append(cap)
        
        for cap in update.removed_capabilities:
            if cap in current_caps:
                current_caps.remove(cap)
        
        # Update agent contract if exists
        if update.agent_id in self.agent_contracts:
            contract = self.agent_contracts[update.agent_id]
            contract.capabilities["current"] = current_caps
            
            # Trigger context injection if needed
            if update.added_capabilities:
                await self._inject_capability_context(update.agent_id, update.added_capabilities)
        
        return {
            "success": True,
            "message": "Capabilities updated",
            "agent_id": update.agent_id,
            "current_capabilities": current_caps
        }
    
    async def inject_context(
        self, injection: ContextInjection
    ) -> Dict[str, Any]:
        """Inject context dynamically into agent."""
        
        if injection.agent_id not in self.agent_contracts:
            raise ValueError(f"No active contract for agent: {injection.agent_id}")
        
        contract = self.agent_contracts[injection.agent_id]
        
        # Apply context injection based on type
        if injection.context_type == "system_prompt":
            if injection.action == "add":
                contract.system_prompt_addition += f"\n\n{injection.context_data.get('content', '')}"
            elif injection.action == "replace":
                contract.system_prompt_addition = injection.context_data.get('content', '')
        
        elif injection.context_type == "behavioral_rules":
            rules = injection.context_data.get('rules', [])
            if injection.action == "add":
                contract.behavioral_rules.extend(rules)
            elif injection.action == "replace":
                contract.behavioral_rules = rules
        
        elif injection.context_type == "constraints":
            constraints = injection.context_data.get('constraints', [])
            if injection.action == "add":
                contract.constraints.extend(constraints)
            elif injection.action == "replace":
                contract.constraints = constraints
        
        return {
            "success": True,
            "message": f"Context {injection.action}ed for {injection.context_type}",
            "agent_id": injection.agent_id,
            "priority": injection.priority,
            "timestamp": injection.timestamp
        }
    
    async def _apply_modifications(
        self, contract: IntegrationContract, modifications: List[Dict[str, Any]]
    ) -> Optional[IntegrationContract]:
        """Apply requested modifications to contract."""
        
        modified_contract = contract  # Copy in real implementation
        
        for mod in modifications:
            mod_type = mod.get("type")
            mod_target = mod.get("target")
            mod_value = mod.get("value")
            
            if mod_type == "add_tool" and mod_target in contract.tools:
                # Can't add tools that don't exist
                continue
            elif mod_type == "remove_tool" and mod_target in contract.tools:
                # Allow removing non-essential tools
                if mod_target not in ["handshake", "register_agent", "request_next_task"]:
                    del modified_contract.tools[mod_target]
            elif mod_type == "modify_workflow" and mod_target == "phases":
                # Allow workflow customization within limits
                pass  # Implementation would validate and apply
        
        return modified_contract
    
    async def _inject_capability_context(
        self, agent_id: str, new_capabilities: List[str]
    ) -> None:
        """Automatically inject context for new capabilities."""
        
        capability_contexts = {
            "testing": "Always write tests before implementation and ensure 80% coverage",
            "security": "Follow security best practices and validate all inputs",
            "performance": "Monitor performance metrics and optimize critical paths",
            "documentation": "Document all public APIs and architectural decisions"
        }
        
        additional_rules = []
        for cap in new_capabilities:
            if cap in capability_contexts:
                additional_rules.append(capability_contexts[cap])
        
        if additional_rules:
            injection = ContextInjection(
                agent_id=agent_id,
                context_type="behavioral_rules",
                context_data={"rules": additional_rules},
                action="add",
                priority="normal"
            )
            await self.inject_context(injection)


# Global protocol extension handler
protocol_handler = ProtocolExtensionHandler()


async def process_protocol_message(
    message_type: str, data: Dict[str, Any]
) -> Dict[str, Any]:
    """Process custom Marcus protocol messages."""
    
    try:
        msg_type = ProtocolMessageType(message_type)
    except ValueError:
        raise ValueError(f"Unknown protocol message type: {message_type}")
    
    if msg_type == ProtocolMessageType.ANNOUNCE:
        announcement = AgentAnnouncement(**data)
        offer = await protocol_handler.handle_agent_announcement(announcement)
        return {
            "type": ProtocolMessageType.CONTRACT_OFFER.value,
            "data": {
                "contract_id": offer.contract_id,
                "contract_version": offer.contract_version,
                "agent_type": offer.agent_type.value,
                "contract": offer.contract.__dict__,
                "negotiable_terms": offer.negotiable_terms,
                "expiry": offer.expiry
            }
        }
    
    elif msg_type == ProtocolMessageType.CONTRACT_ACCEPT:
        response = ContractResponse(**data, accepted=True)
        result = await protocol_handler.handle_contract_response(response)
        return {"type": "marcus/contract_result", "data": result}
    
    elif msg_type == ProtocolMessageType.CONTRACT_REJECT:
        response = ContractResponse(**data, accepted=False)
        result = await protocol_handler.handle_contract_response(response)
        return {"type": "marcus/contract_result", "data": result}
    
    elif msg_type == ProtocolMessageType.CAPABILITY_UPDATE:
        update = CapabilityUpdate(**data)
        result = await protocol_handler.handle_capability_update(update)
        return {"type": "marcus/capability_result", "data": result}
    
    elif msg_type == ProtocolMessageType.CONTEXT_INJECTION:
        injection = ContextInjection(**data)
        result = await protocol_handler.inject_context(injection)
        return {"type": "marcus/context_result", "data": result}
    
    else:
        raise ValueError(f"Unhandled message type: {msg_type}")


def create_announcement_message(
    agent_id: str, 
    agent_type: str, 
    capabilities: List[str],
    version: str = "1.0"
) -> Dict[str, Any]:
    """Helper to create agent announcement message."""
    
    return {
        "jsonrpc": "2.0",
        "method": ProtocolMessageType.ANNOUNCE.value,
        "params": {
            "agent_id": agent_id,
            "agent_type": agent_type,
            "version": version,
            "capabilities": capabilities
        },
        "id": f"announce_{agent_id}_{datetime.utcnow().strftime('%H%M%S')}"
    }


def create_contract_response(
    contract_id: str,
    agent_id: str, 
    accepted: bool,
    modifications: List[Dict[str, Any]] = None,
    reason: str = ""
) -> Dict[str, Any]:
    """Helper to create contract response message."""
    
    message_type = (
        ProtocolMessageType.CONTRACT_ACCEPT if accepted 
        else ProtocolMessageType.CONTRACT_REJECT
    )
    
    params = {
        "contract_id": contract_id,
        "agent_id": agent_id,
        "accepted": accepted
    }
    
    if not accepted:
        params["reason"] = reason
        if modifications:
            params["requested_modifications"] = modifications
    
    return {
        "jsonrpc": "2.0", 
        "method": message_type.value,
        "params": params,
        "id": f"response_{contract_id}_{agent_id}"
    }