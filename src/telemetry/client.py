"""
Privacy-Preserving Telemetry Client for PM Agent

This client collects strategic intelligence while maintaining strict privacy standards.
It focuses on insights that provide competitive advantages:

1. Project failure prediction patterns
2. Optimal team composition insights
3. Workflow efficiency benchmarks  
4. AI decision quality feedback
5. Resource allocation optimization
6. Market trend signals

All data is anonymized, aggregated, and encrypted before transmission.
Users have full control and must explicitly opt-in.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
try:
    import aiohttp
    import ssl
    from cryptography.fernet import Fernet
    HAS_CRYPTO = True
except ImportError:
    # Fallback for testing - use simple base64 encoding
    import base64
    HAS_CRYPTO = False
    
    class Fernet:
        def __init__(self, key):
            self.key = key
        
        def encrypt(self, data):
            # Simple base64 encoding for testing
            return base64.b64encode(data)
        
        @staticmethod
        def generate_key():
            return base64.b64encode(b"test-key-for-telemetry-testing")
    
    aiohttp = None
    ssl = None

from .strategic_collector import StrategicIntelligenceCollector, StrategicInsight, InsightCategory
from .anonymizer import DataAnonymizer
from .consent import ConsentManager
from src.core.models import ProjectState, WorkerStatus


class TelemetryClient:
    """
    Privacy-preserving telemetry client for strategic intelligence collection
    
    Key Features:
    - Opt-in only with granular consent
    - Local-first processing and anonymization
    - Batch transmission with encryption
    - Strategic focus on competitive intelligence
    - Full user control and transparency
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize telemetry client with privacy-first defaults"""
        self.config_path = config_path or "~/.pm-agent/telemetry.json"
        self.config = self._load_config()
        
        # Core components
        self.strategic_collector = StrategicIntelligenceCollector()
        self.anonymizer = DataAnonymizer()
        self.consent_manager = ConsentManager(self.config.get('consent', {}))
        
        # State
        self.installation_id = self._get_or_create_installation_id()
        self.pending_insights: List[StrategicInsight] = []
        self.transmission_task: Optional[asyncio.Task] = None
        self.enabled = False
        
        # Encryption
        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher = Fernet(self.encryption_key)
        
        # Logger
        self.logger = logging.getLogger(__name__)
        
        # Initialize based on consent
        self._initialize_from_consent()
    
    async def initialize(self) -> None:
        """Initialize telemetry client"""
        if not self.enabled:
            self.logger.info("Telemetry disabled - respecting user privacy choice")
            return
            
        # Start background transmission task
        if self.config.get('auto_transmit', True):
            self.transmission_task = asyncio.create_task(self._transmission_loop())
            
        self.logger.info("Privacy-preserving telemetry initialized")
    
    async def shutdown(self) -> None:
        """Shutdown telemetry client gracefully"""
        if self.transmission_task:
            self.transmission_task.cancel()
            try:
                await self.transmission_task
            except asyncio.CancelledError:
                pass
                
        # Transmit any pending insights if user consented
        if self.enabled and self.pending_insights:
            await self._transmit_insights(force=True)
    
    # Strategic Intelligence Collection Methods
    
    async def collect_project_health_insight(
        self,
        project_state: ProjectState,
        health_history: List[Dict[str, Any]],
        team_status: List[WorkerStatus],
        ai_recommendations: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """
        Collect strategic insights from project health data
        
        Strategic Value:
        - Build world's most accurate failure prediction model
        - Discover optimal team composition patterns
        - Identify workflow efficiency benchmarks
        """
        if not self._has_consent_for(InsightCategory.FAILURE_PREDICTION):
            return
            
        try:
            # Collect comprehensive project insights
            insights = self.strategic_collector.collect_project_lifecycle_insight(
                project_state, health_history, team_status
            )
            
            # Add AI effectiveness insights if available
            if ai_recommendations and self._has_consent_for(InsightCategory.AI_EFFECTIVENESS):
                for recommendation in ai_recommendations:
                    ai_insight = self.strategic_collector.collect_ai_decision_feedback(
                        recommendation,
                        recommendation.get('user_action', 'unknown'),
                        recommendation.get('outcome_success', False),
                        {
                            'total_tasks': project_state.total_tasks,
                            'team_size': len(team_status),
                            'risk_level': project_state.risk_level.value,
                            'project_type': 'software_development'  # Could be inferred
                        }
                    )
                    insights.append(ai_insight)
            
            # Anonymize and queue insights
            for insight in insights:
                anonymized_insight = self.anonymizer.anonymize_insight(insight)
                self._queue_insight(anonymized_insight)
                
            self.logger.debug(f"Collected {len(insights)} strategic insights")
            
        except Exception as e:
            self.logger.error(f"Failed to collect project health insights: {e}")
    
    async def collect_workflow_optimization_insight(
        self,
        task_transitions: List[Dict[str, Any]],
        resolution_times: Dict[str, float],
        team_structure: Dict[str, Any],
        bottleneck_events: List[Dict[str, Any]]
    ) -> None:
        """
        Collect workflow optimization insights
        
        Strategic Value:
        - Identify industry-specific optimization patterns
        - Build workflow efficiency benchmarks
        - Predict and prevent bottlenecks
        """
        if not self._has_consent_for(InsightCategory.WORKFLOW_EFFICIENCY):
            return
            
        try:
            # Collect workflow insights
            workflow_insight = self.strategic_collector.collect_workflow_bottleneck_patterns(
                task_transitions, resolution_times, team_structure
            )
            
            # Anonymize and queue
            anonymized_insight = self.anonymizer.anonymize_insight(workflow_insight)
            self._queue_insight(anonymized_insight)
            
            self.logger.debug("Collected workflow optimization insight")
            
        except Exception as e:
            self.logger.error(f"Failed to collect workflow insights: {e}")
    
    async def collect_resource_optimization_insight(
        self,
        capacity_data: List[float],
        performance_data: List[float],
        satisfaction_data: Optional[List[float]] = None,
        burnout_indicators: Optional[List[bool]] = None
    ) -> None:
        """
        Collect resource allocation optimization insights
        
        Strategic Value:
        - Discover optimal capacity utilization formulas
        - Prevent burnout while maximizing performance
        - Build predictive models for resource planning
        """
        if not self._has_consent_for(InsightCategory.RESOURCE_OPTIMIZATION):
            return
            
        try:
            # Collect resource optimization insights
            resource_insight = self.strategic_collector.collect_resource_optimization_patterns(
                capacity_data, performance_data, satisfaction_data
            )
            
            # Anonymize and queue
            anonymized_insight = self.anonymizer.anonymize_insight(resource_insight)
            self._queue_insight(anonymized_insight)
            
            self.logger.debug("Collected resource optimization insight")
            
        except Exception as e:
            self.logger.error(f"Failed to collect resource insights: {e}")
    
    async def collect_feature_usage_insight(
        self,
        feature_usage: Dict[str, int],
        user_behavior: Dict[str, Any],
        adoption_patterns: Dict[str, float]
    ) -> None:
        """
        Collect market trend and feature adoption insights
        
        Strategic Value:
        - Predict feature demand before competitors
        - Identify emerging market trends
        - Guide product development priorities
        """
        if not self._has_consent_for(InsightCategory.MARKET_TRENDS):
            return
            
        try:
            # Collect market trend insights
            market_insight = self.strategic_collector.collect_market_trend_signals(
                feature_usage, user_behavior, adoption_patterns
            )
            
            # Anonymize and queue
            anonymized_insight = self.anonymizer.anonymize_insight(market_insight)
            self._queue_insight(anonymized_insight)
            
            self.logger.debug("Collected market trend insight")
            
        except Exception as e:
            self.logger.error(f"Failed to collect market insights: {e}")
    
    async def record_ai_decision_outcome(
        self,
        decision_id: str,
        recommendation: Dict[str, Any],
        user_action: str,
        outcome_success: bool,
        context: Dict[str, Any]
    ) -> None:
        """
        Record AI decision outcome for continuous improvement
        
        Strategic Value:
        - Build self-improving AI that gets better with scale
        - Outpace competitors with static AI models
        - Increase AI recommendation acceptance rates
        """
        if not self._has_consent_for(InsightCategory.AI_EFFECTIVENESS):
            return
            
        try:
            # Collect AI feedback
            ai_insight = self.strategic_collector.collect_ai_decision_feedback(
                recommendation, user_action, outcome_success, context
            )
            
            # Anonymize and queue
            anonymized_insight = self.anonymizer.anonymize_insight(ai_insight)
            self._queue_insight(anonymized_insight)
            
            self.logger.debug(f"Recorded AI decision outcome for {decision_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to record AI decision outcome: {e}")
    
    # Privacy and Consent Management
    
    def request_consent(self, categories: List[InsightCategory]) -> Dict[str, Any]:
        """
        Request user consent for specific data collection categories
        
        Returns consent request that should be presented to user
        """
        return self.consent_manager.create_consent_request(categories)
    
    def update_consent(self, consent_response: Dict[str, Any]) -> None:
        """Update user consent based on their response"""
        self.consent_manager.update_consent(consent_response)
        self._save_config()
        self._initialize_from_consent()
    
    def get_consent_status(self) -> Dict[str, Any]:
        """Get current consent status"""
        return self.consent_manager.get_consent_status()
    
    def revoke_all_consent(self) -> None:
        """Revoke all telemetry consent"""
        self.consent_manager.revoke_all_consent()
        self.enabled = False
        self._save_config()
        
        # Clear pending data
        self.pending_insights.clear()
        
        self.logger.info("All telemetry consent revoked")
    
    def _has_consent_for(self, category: InsightCategory) -> bool:
        """Check if user has consented to specific category"""
        return self.enabled and self.consent_manager.has_consent_for(category)
    
    # Data Transmission
    
    async def _transmission_loop(self) -> None:
        """Background loop for transmitting insights"""
        interval = self.config.get('transmission_interval', 86400)  # 24 hours default
        
        while True:
            try:
                await asyncio.sleep(interval)
                
                if self.pending_insights:
                    await self._transmit_insights()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Transmission loop error: {e}")
                # Continue loop after error
    
    async def _transmit_insights(self, force: bool = False) -> None:
        """Transmit queued insights to telemetry server"""
        if not self.pending_insights:
            return
            
        # Only transmit if we have enough insights or force is True
        min_batch_size = self.config.get('min_batch_size', 10)
        if not force and len(self.pending_insights) < min_batch_size:
            return
            
        try:
            # Prepare transmission payload
            payload = {
                'installation_id': self.installation_id,
                'timestamp': datetime.now().isoformat(),
                'insights': [insight.data for insight in self.pending_insights],
                'privacy_version': '1.0',
                'client_version': '1.0.0'
            }
            
            # Encrypt payload
            encrypted_payload = self.cipher.encrypt(
                json.dumps(payload).encode()
            )
            
            # Skip actual transmission if aiohttp not available (testing mode)
            if aiohttp is None:
                self.logger.info(f"Simulated transmission of {len(self.pending_insights)} insights (testing mode)")
                transmitted_count = len(self.pending_insights)
                self.pending_insights.clear()
                return
            
            # Transmit
            endpoint = self.config.get('endpoint', 'https://telemetry.pm-agent.dev/v1/insights')
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint,
                    data=encrypted_payload,
                    headers={
                        'Content-Type': 'application/octet-stream',
                        'X-Privacy-Version': '1.0',
                        'X-Client-Version': '1.0.0'
                    },
                    ssl=self._get_ssl_context(),
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        # Clear transmitted insights
                        transmitted_count = len(self.pending_insights)
                        self.pending_insights.clear()
                        self.logger.info(f"Transmitted {transmitted_count} insights successfully")
                    else:
                        self.logger.warning(f"Transmission failed with status {response.status}")
                        
        except Exception as e:
            self.logger.error(f"Failed to transmit insights: {e}")
    
    def _queue_insight(self, insight: StrategicInsight) -> None:
        """Queue insight for transmission"""
        self.pending_insights.append(insight)
        
        # Limit queue size
        max_queue_size = self.config.get('max_queue_size', 1000)
        if len(self.pending_insights) > max_queue_size:
            # Remove oldest insights
            self.pending_insights = self.pending_insights[-max_queue_size:]
    
    # Configuration and State Management
    
    def _load_config(self) -> Dict[str, Any]:
        """Load telemetry configuration"""
        config_file = Path(self.config_path).expanduser()
        
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Failed to load config: {e}")
                
        # Default config (privacy-first)
        return {
            'enabled': False,  # Opt-in only
            'consent': {},
            'auto_transmit': True,
            'transmission_interval': 86400,  # 24 hours
            'min_batch_size': 10,
            'max_queue_size': 1000,
            'endpoint': 'https://telemetry.pm-agent.dev/v1/insights'
        }
    
    def _save_config(self) -> None:
        """Save telemetry configuration"""
        config_file = Path(self.config_path).expanduser()
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Include consent data in config
            config_with_consent = self.config.copy()
            config_with_consent['consent'] = self.consent_manager.consent_data
            
            with open(config_file, 'w') as f:
                json.dump(config_with_consent, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")
    
    def _get_or_create_installation_id(self) -> str:
        """Get or create anonymous installation ID"""
        if 'installation_id' in self.config:
            return self.config['installation_id']
            
        # Create new anonymous ID
        installation_id = str(uuid.uuid4())
        self.config['installation_id'] = installation_id
        self._save_config()
        
        return installation_id
    
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for data transmission"""
        if 'encryption_key' in self.config:
            return self.config['encryption_key'].encode()
            
        # Create new encryption key
        key = Fernet.generate_key()
        self.config['encryption_key'] = key.decode()
        self._save_config()
        
        return key
    
    def _initialize_from_consent(self) -> None:
        """Initialize client based on current consent"""
        consent_status = self.consent_manager.get_consent_status()
        self.enabled = consent_status.get('any_consent_given', False)
        
        if self.enabled:
            self.logger.info("Telemetry enabled based on user consent")
        else:
            self.logger.info("Telemetry disabled - no consent given")
    
    def _get_ssl_context(self):
        """Create SSL context for secure transmission"""
        if ssl is None:
            return None
        context = ssl.create_default_context()
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        return context
    
    # Public API for strategic insights summary
    
    def get_collected_insights_summary(self) -> Dict[str, Any]:
        """Get summary of collected insights (for transparency)"""
        if not self.enabled:
            return {'status': 'disabled', 'message': 'Telemetry disabled by user choice'}
            
        categories = {}
        for insight in self.pending_insights:
            category = insight.category.value
            if category not in categories:
                categories[category] = {'count': 0, 'avg_confidence': 0.0}
            categories[category]['count'] += 1
            categories[category]['avg_confidence'] += insight.confidence_score
            
        # Calculate averages
        for category_data in categories.values():
            if category_data['count'] > 0:
                category_data['avg_confidence'] /= category_data['count']
                
        return {
            'status': 'active',
            'pending_insights': len(self.pending_insights),
            'categories': categories,
            'next_transmission': 'within_24h',
            'privacy_level': 'maximum'
        }