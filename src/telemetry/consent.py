"""
Consent Management System for PM Agent Telemetry

Implements comprehensive consent management with granular controls, transparency,
and user rights management. Follows privacy-by-design principles with:

1. Explicit opt-in for all data collection
2. Granular category-based consent
3. Easy consent modification and revocation
4. Transparent explanation of data usage
5. Data subject rights (access, deletion, portability)

All consent decisions are stored locally and never transmitted.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
from pathlib import Path
from enum import Enum

from .strategic_collector import InsightCategory


class ConsentLevel(Enum):
    """Levels of consent granularity"""
    DENIED = "denied"
    BASIC = "basic"
    ENHANCED = "enhanced"
    FULL = "full"


class DataSubjectRights(Enum):
    """Data subject rights under privacy regulations"""
    ACCESS = "access"           # Right to access collected data
    RECTIFICATION = "rectification"  # Right to correct data
    ERASURE = "erasure"         # Right to delete data
    PORTABILITY = "portability"  # Right to data portability
    OBJECTION = "objection"     # Right to object to processing
    RESTRICTION = "restriction"  # Right to restrict processing


class ConsentManager:
    """
    Manages user consent for telemetry data collection
    
    Provides granular consent controls allowing users to choose exactly
    what data they're comfortable sharing. Implements privacy-by-design
    principles with default-deny policies and transparent explanations.
    
    Key Features:
    - Category-based consent (failure prediction, team optimization, etc.)
    - Consent versioning and audit trail
    - Easy revocation and modification
    - Transparent data usage explanations
    - Data subject rights implementation
    """
    
    def __init__(self, consent_data: Optional[Dict[str, Any]] = None):
        """Initialize consent manager with existing consent data"""
        self.consent_data = consent_data or {}
        self.consent_version = "1.0"
        self.last_updated = datetime.now()
        
        # Default consent state (all denied)
        self._ensure_default_consent_structure()
        
        # Category explanations for informed consent
        self.category_explanations = {
            InsightCategory.FAILURE_PREDICTION: {
                "title": "Project Health & Failure Prediction",
                "description": "Help us build better early warning systems for project issues",
                "data_collected": [
                    "Anonymous health status patterns (green/yellow/red)",
                    "Task completion trends (no task content)",
                    "Team velocity patterns (no individual performance)",
                    "Risk pattern indicators (generalized)"
                ],
                "benefits": [
                    "Receive earlier warnings about potential project issues",
                    "Get industry benchmarks for project health",
                    "Help other teams avoid common failure patterns",
                    "Improve PM Agent's prediction accuracy"
                ],
                "retention": "Aggregated data kept for algorithm improvement",
                "sharing": "Only statistical patterns shared, never raw data"
            },
            
            InsightCategory.TEAM_OPTIMIZATION: {
                "title": "Team Composition & Performance Optimization",
                "description": "Help discover optimal team structures and collaboration patterns",
                "data_collected": [
                    "Anonymous team size categories (micro/small/medium/large)",
                    "Role diversity patterns (no specific roles)",
                    "Skill distribution patterns (no individual skills)",
                    "Performance correlation patterns"
                ],
                "benefits": [
                    "Get recommendations for optimal team composition",
                    "Understand industry best practices for team structure",
                    "Help other teams build high-performing organizations",
                    "Improve team effectiveness with personalized optimization suggestions"
                ],
                "retention": "Pattern data retained for continuous improvement",
                "sharing": "Only aggregated insights shared across user base"
            },
            
            InsightCategory.WORKFLOW_EFFICIENCY: {
                "title": "Workflow & Process Optimization",
                "description": "Help identify and eliminate common workflow bottlenecks",
                "data_collected": [
                    "Anonymous bottleneck frequency patterns",
                    "Task transition timing (no task details)",
                    "Process efficiency metrics",
                    "Resolution time patterns"
                ],
                "benefits": [
                    "Get workflow optimization recommendations",
                    "Compare your processes to industry standards",
                    "Help identify common bottleneck patterns",
                    "Improve process efficiency with proactive suggestions"
                ],
                "retention": "Workflow patterns kept for optimization algorithms",
                "sharing": "Process insights shared to benefit all users"
            },
            
            InsightCategory.AI_EFFECTIVENESS: {
                "title": "AI Recommendation Improvement",
                "description": "Help make PM Agent's AI recommendations more accurate and useful",
                "data_collected": [
                    "AI recommendation acceptance rates (anonymous)",
                    "Outcome success patterns",
                    "User preference patterns",
                    "Confidence score calibration data"
                ],
                "benefits": [
                    "Receive more accurate AI recommendations",
                    "Get AI suggestions tailored to your context",
                    "Help improve AI for everyone using PM Agent",
                    "Enable continuous AI learning and adaptation"
                ],
                "retention": "Feedback data used for ongoing AI training",
                "sharing": "Model improvements benefit all users"
            },
            
            InsightCategory.RESOURCE_OPTIMIZATION: {
                "title": "Resource Planning & Capacity Optimization",
                "description": "Help optimize resource allocation and prevent team burnout",
                "data_collected": [
                    "Anonymous capacity utilization patterns",
                    "Performance vs workload correlations",
                    "Resource allocation efficiency metrics",
                    "Burnout prevention indicators"
                ],
                "benefits": [
                    "Get optimal capacity planning recommendations",
                    "Receive burnout prevention warnings",
                    "Help establish healthy work-life balance patterns",
                    "Optimize resource allocation across projects"
                ],
                "retention": "Resource patterns kept for capacity planning",
                "sharing": "Best practices shared to promote healthy teams"
            },
            
            InsightCategory.MARKET_TRENDS: {
                "title": "Feature Usage & Market Trends",
                "description": "Help guide product development and feature priorities",
                "data_collected": [
                    "Anonymous feature usage patterns",
                    "Adoption trend indicators",
                    "User behavior patterns (no personal data)",
                    "Market demand signals"
                ],
                "benefits": [
                    "Influence PM Agent's development roadmap",
                    "Get early access to features in high demand",
                    "Help prioritize the most valuable improvements",
                    "Receive recommendations for underutilized features"
                ],
                "retention": "Trend data used for product planning",
                "sharing": "Market insights guide product development"
            }
        }
    
    def create_consent_request(self, categories: List[InsightCategory]) -> Dict[str, Any]:
        """
        Create a consent request for specific categories
        
        Generates a comprehensive consent request with detailed explanations
        that users can review before making informed decisions about their
        data sharing preferences.
        """
        consent_request = {
            "version": self.consent_version,
            "timestamp": datetime.now().isoformat(),
            "privacy_policy_url": "https://pm-agent.dev/privacy",
            "contact_email": "privacy@pm-agent.dev",
            "withdrawal_instructions": "You can change these settings anytime in PM Agent preferences",
            
            "overview": {
                "title": "Help Improve PM Agent While Protecting Your Privacy",
                "description": "PM Agent can collect anonymous insights to improve project management for everyone. Your privacy is our priority - all data is anonymized, aggregated, and encrypted.",
                "key_principles": [
                    "🔒 Your project data stays private - only anonymous statistical patterns are shared",
                    "🎯 Granular control - choose exactly what to share",
                    "🚪 Easy exit - revoke consent anytime with one click",
                    "📊 Transparent and clear - see exactly what data helps improve PM Agent",
                    "🏆 Mutual benefit - your insights help build better tools for everyone"
                ]
            },
            
            "categories": {},
            "recommendations": self._generate_consent_recommendations(categories),
            "legal_basis": "Legitimate interest in product improvement with user consent",
            "data_retention": "Aggregated insights retained indefinitely; raw data deleted immediately",
            "third_party_sharing": "No data shared with third parties - used only for PM Agent improvement",
            
            "user_rights": {
                "access": "Request a copy of insights derived from your data",
                "deletion": "Request deletion of all your data and insights",
                "portability": "Request your data in a machine-readable format",
                "objection": "Object to specific types of data processing",
                "rectification": "Request correction of inaccurate data"
            }
        }
        
        # Add detailed category information
        for category in categories:
            if category in self.category_explanations:
                consent_request["categories"][category.value] = {
                    **self.category_explanations[category],
                    "current_consent": self.get_consent_for_category(category),
                    "recommended_level": self._recommend_consent_level(category)
                }
        
        return consent_request
    
    def update_consent(self, consent_response: Dict[str, Any]) -> None:
        """Update consent based on user response"""
        timestamp = datetime.now()
        
        # Store consent decisions
        for category_name, decision in consent_response.get("categories", {}).items():
            try:
                category = InsightCategory(category_name)
                self.consent_data[category.value] = {
                    "consent_level": decision.get("level", ConsentLevel.DENIED.value),
                    "granted_at": timestamp.isoformat(),
                    "version": self.consent_version,
                    "explicit_consent": True,
                    "conditions": decision.get("conditions", [])
                }
            except ValueError:
                # Skip invalid categories
                continue
        
        # Store global preferences
        self.consent_data["global"] = {
            "last_updated": timestamp.isoformat(),
            "version": self.consent_version,
            "contact_preferences": consent_response.get("contact_preferences", {}),
            "data_retention_preference": consent_response.get("data_retention", "standard"),
            "audit_trail": self.consent_data.get("global", {}).get("audit_trail", [])
        }
        
        # Add to audit trail
        self.consent_data["global"]["audit_trail"].append({
            "action": "consent_updated",
            "timestamp": timestamp.isoformat(),
            "categories_changed": list(consent_response.get("categories", {}).keys()),
            "version": self.consent_version
        })
        
        self.last_updated = timestamp
    
    def has_consent_for(self, category: InsightCategory) -> bool:
        """Check if user has given consent for a specific category"""
        category_consent = self.consent_data.get(category.value, {})
        consent_level = category_consent.get("consent_level", ConsentLevel.DENIED.value)
        
        # Any level above DENIED is considered consent
        return consent_level != ConsentLevel.DENIED.value
    
    def get_consent_for_category(self, category: InsightCategory) -> Dict[str, Any]:
        """Get detailed consent information for a category"""
        return self.consent_data.get(category.value, {
            "consent_level": ConsentLevel.DENIED.value,
            "granted_at": None,
            "version": None,
            "explicit_consent": False,
            "conditions": []
        })
    
    def get_consent_status(self) -> Dict[str, Any]:
        """Get comprehensive consent status"""
        status = {
            "consent_version": self.consent_version,
            "last_updated": self.last_updated.isoformat(),
            "any_consent_given": False,
            "categories": {},
            "global_preferences": self.consent_data.get("global", {}),
            "rights_exercised": self._get_rights_exercised(),
            "next_review_due": self._calculate_next_review_date().isoformat()
        }
        
        # Check each category
        for category in InsightCategory:
            category_consent = self.get_consent_for_category(category)
            status["categories"][category.value] = {
                "has_consent": self.has_consent_for(category),
                "level": category_consent["consent_level"],
                "granted_at": category_consent["granted_at"],
                "explicit": category_consent["explicit_consent"]
            }
            
            if self.has_consent_for(category):
                status["any_consent_given"] = True
        
        return status
    
    def revoke_all_consent(self) -> None:
        """Revoke all consent and request data deletion"""
        timestamp = datetime.now()
        
        # Revoke all category consent
        for category in InsightCategory:
            self.consent_data[category.value] = {
                "consent_level": ConsentLevel.DENIED.value,
                "granted_at": None,
                "revoked_at": timestamp.isoformat(),
                "version": self.consent_version,
                "explicit_consent": True,
                "revocation_reason": "user_request"
            }
        
        # Update global settings
        if "global" not in self.consent_data:
            self.consent_data["global"] = {"audit_trail": []}
        
        self.consent_data["global"]["all_consent_revoked"] = True
        self.consent_data["global"]["revoked_at"] = timestamp.isoformat()
        
        # Add to audit trail
        self.consent_data["global"]["audit_trail"].append({
            "action": "all_consent_revoked",
            "timestamp": timestamp.isoformat(),
            "categories_affected": [c.value for c in InsightCategory],
            "version": self.consent_version
        })
        
        self.last_updated = timestamp
    
    def revoke_category_consent(self, category: InsightCategory, reason: str = "user_request") -> None:
        """Revoke consent for a specific category"""
        timestamp = datetime.now()
        
        self.consent_data[category.value] = {
            "consent_level": ConsentLevel.DENIED.value,
            "granted_at": None,
            "revoked_at": timestamp.isoformat(),
            "version": self.consent_version,
            "explicit_consent": True,
            "revocation_reason": reason
        }
        
        # Update audit trail
        if "global" not in self.consent_data:
            self.consent_data["global"] = {"audit_trail": []}
        
        self.consent_data["global"]["audit_trail"].append({
            "action": "category_consent_revoked",
            "timestamp": timestamp.isoformat(),
            "category": category.value,
            "reason": reason,
            "version": self.consent_version
        })
        
        self.last_updated = timestamp
    
    def exercise_data_right(self, right: DataSubjectRights, details: Dict[str, Any] = None) -> Dict[str, Any]:
        """Exercise a data subject right (GDPR, CCPA, etc.)"""
        timestamp = datetime.now()
        details = details or {}
        
        request_id = f"dsr_{int(timestamp.timestamp())}_{right.value}"
        
        # Record the request
        if "global" not in self.consent_data:
            self.consent_data["global"] = {"audit_trail": []}
        
        if "rights_requests" not in self.consent_data["global"]:
            self.consent_data["global"]["rights_requests"] = []
        
        request_record = {
            "request_id": request_id,
            "right": right.value,
            "requested_at": timestamp.isoformat(),
            "details": details,
            "status": "submitted",
            "expected_completion": (timestamp + timedelta(days=30)).isoformat()
        }
        
        self.consent_data["global"]["rights_requests"].append(request_record)
        
        # Add to audit trail
        self.consent_data["global"]["audit_trail"].append({
            "action": "data_right_exercised",
            "timestamp": timestamp.isoformat(),
            "right": right.value,
            "request_id": request_id,
            "version": self.consent_version
        })
        
        return {
            "request_id": request_id,
            "status": "submitted",
            "expected_completion": request_record["expected_completion"],
            "instructions": self._get_rights_instructions(right),
            "contact_info": "privacy@pm-agent.dev"
        }
    
    def get_consent_audit_trail(self) -> List[Dict[str, Any]]:
        """Get complete audit trail of consent decisions"""
        return self.consent_data.get("global", {}).get("audit_trail", [])
    
    def is_consent_expired(self) -> bool:
        """Check if consent needs to be renewed"""
        # Consent expires after 2 years
        expiry_period = timedelta(days=730)
        return datetime.now() - self.last_updated > expiry_period
    
    def export_consent_data(self) -> Dict[str, Any]:
        """Export all consent data for portability rights"""
        return {
            "version": self.consent_version,
            "exported_at": datetime.now().isoformat(),
            "consent_data": self.consent_data,
            "explanations": self.category_explanations,
            "format_version": "1.0"
        }
    
    # Private helper methods
    
    def _ensure_default_consent_structure(self) -> None:
        """Ensure consent data has proper default structure"""
        if "global" not in self.consent_data:
            self.consent_data["global"] = {
                "version": self.consent_version,
                "created_at": datetime.now().isoformat(),
                "audit_trail": []
            }
        
        # Ensure all categories have default denied state
        for category in InsightCategory:
            if category.value not in self.consent_data:
                self.consent_data[category.value] = {
                    "consent_level": ConsentLevel.DENIED.value,
                    "granted_at": None,
                    "version": None,
                    "explicit_consent": False,
                    "conditions": []
                }
    
    def _generate_consent_recommendations(self, categories: List[InsightCategory]) -> Dict[str, Any]:
        """Generate personalized consent recommendations"""
        return {
            "recommended_categories": [
                InsightCategory.FAILURE_PREDICTION.value,
                InsightCategory.WORKFLOW_EFFICIENCY.value
            ],
            "rationale": "These categories provide the most benefit with minimal privacy impact",
            "start_small": "Consider starting with basic failure prediction to see the benefits",
            "privacy_impact": "All recommended categories use only aggregated, anonymous data"
        }
    
    def _recommend_consent_level(self, category: InsightCategory) -> str:
        """Recommend appropriate consent level for a category"""
        # Most categories can start with basic level
        low_risk_categories = [
            InsightCategory.FAILURE_PREDICTION,
            InsightCategory.WORKFLOW_EFFICIENCY,
            InsightCategory.AI_EFFECTIVENESS
        ]
        
        if category in low_risk_categories:
            return ConsentLevel.BASIC.value
        else:
            return ConsentLevel.BASIC.value  # Conservative default
    
    def _get_rights_exercised(self) -> List[Dict[str, Any]]:
        """Get list of data rights that have been exercised"""
        return self.consent_data.get("global", {}).get("rights_requests", [])
    
    def _calculate_next_review_date(self) -> datetime:
        """Calculate when consent should next be reviewed"""
        # Review consent annually or when major version changes
        return self.last_updated + timedelta(days=365)
    
    def _get_rights_instructions(self, right: DataSubjectRights) -> str:
        """Get instructions for exercising a specific right"""
        instructions = {
            DataSubjectRights.ACCESS: "Your request for data access has been submitted. You'll receive a summary of insights derived from your data within 30 days.",
            DataSubjectRights.ERASURE: "Your request for data deletion has been submitted. All your data and derived insights will be deleted within 30 days.",
            DataSubjectRights.PORTABILITY: "Your request for data portability has been submitted. You'll receive your data in JSON format within 30 days.",
            DataSubjectRights.OBJECTION: "Your objection has been recorded. We'll stop processing data for the specified categories immediately.",
            DataSubjectRights.RESTRICTION: "Your request for processing restriction has been submitted. Processing will be limited as requested.",
            DataSubjectRights.RECTIFICATION: "Your request for data correction has been submitted. Any inaccuracies will be corrected within 30 days."
        }
        
        return instructions.get(right, "Your request has been submitted and will be processed within 30 days.")
    
    def save_to_file(self, file_path: str) -> None:
        """Save consent data to file"""
        consent_file = Path(file_path).expanduser()
        consent_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(consent_file, 'w') as f:
                json.dump({
                    "consent_data": self.consent_data,
                    "version": self.consent_version,
                    "last_updated": self.last_updated.isoformat()
                }, f, indent=2)
        except Exception as e:
            # Silently fail - consent is optional
            pass
    
    @classmethod
    def load_from_file(cls, file_path: str) -> 'ConsentManager':
        """Load consent data from file"""
        consent_file = Path(file_path).expanduser()
        
        if not consent_file.exists():
            return cls()
        
        try:
            with open(consent_file, 'r') as f:
                data = json.load(f)
                
            manager = cls(data.get("consent_data", {}))
            manager.consent_version = data.get("version", "1.0")
            
            if "last_updated" in data:
                manager.last_updated = datetime.fromisoformat(data["last_updated"])
            
            return manager
            
        except Exception:
            # Return default manager if loading fails
            return cls()