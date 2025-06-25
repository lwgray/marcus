# PM Agent Telemetry Privacy Technical Guide

*For Developers and Technical Implementers*

## Overview

This guide provides technical details about PM Agent's privacy-preserving telemetry implementation, including anonymization techniques, privacy controls, and compliance mechanisms.

## Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Data Source   │───▶│   Anonymizer     │───▶│  Telemetry      │
│  (Raw Metrics)  │    │   Pipeline       │    │   Client        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                       ┌────────▼────────┐      ┌────────▼────────┐
                       │  Consent        │      │  Transmission   │
                       │  Manager        │      │  Engine         │
                       └─────────────────┘      └─────────────────┘
```

## Privacy Technologies Implementation

### 1. Differential Privacy

#### Laplace Mechanism
```python
def _add_differential_privacy_noise(self, value: float, data_type: str) -> float:
    """Add calibrated Laplace noise for differential privacy"""
    params = self.noise_params.get(data_type, {'sensitivity': 1.0, 'epsilon': 0.1})
    
    # Laplace mechanism: noise scale = sensitivity / epsilon
    scale = params['sensitivity'] / params['epsilon']
    noise = np.random.laplace(0, scale)
    
    return value + noise
```

#### Noise Parameters by Data Type
| Data Type | Sensitivity | Epsilon | Scale | Privacy Level |
|-----------|-------------|---------|-------|---------------|
| `confidence_score` | 1.0 | 0.1 | 10.0 | High |
| `performance_score` | 1.0 | 0.1 | 10.0 | High |
| `velocity` | 10.0 | 0.2 | 50.0 | Medium |
| `team_size` | 1.0 | 0.2 | 5.0 | Medium |
| `task_count` | 5.0 | 0.2 | 25.0 | Medium |

#### Privacy Budget Management
- **Global Budget**: 1.0 epsilon per user session
- **Category Allocation**: Split across insight categories
- **Budget Tracking**: Prevents privacy budget exhaustion

### 2. K-Anonymity Implementation

#### Group Size Enforcement
```python
def _anonymize_distribution(self, distribution: List[str]) -> List[str]:
    """Ensure k-anonymity in distributions"""
    bucket_counts = {}
    for bucket in distribution:
        bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1
    
    # Only return buckets with sufficient count (k-anonymity)
    filtered_buckets = [
        bucket for bucket, count in bucket_counts.items() 
        if count >= self.k_anonymity
    ]
    
    return filtered_buckets
```

#### Minimum Group Sizes
- **Default K**: 5 (minimum 5 users per insight group)
- **High-sensitivity data**: K = 10
- **Team composition**: K = 5
- **Workflow patterns**: K = 3

### 3. Data Anonymization Pipeline

#### Identifier Removal
```python
def _apply_common_anonymization(self, data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove or hash identifying information"""
    sensitive_keys = ['id', 'user_id', 'project_id', 'team_id', 'name']
    
    for key in list(data.keys()):
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            if isinstance(data[key], str):
                data[key] = self._hash_identifier(data[key])
            else:
                del data[key]
    
    return data
```

#### Secure Hashing
```python
def _hash_identifier(self, identifier: str) -> str:
    """Create consistent anonymous hash"""
    combined = f"{identifier}:{self.secret_key}"
    hash_value = hashlib.sha256(combined.encode()).hexdigest()
    return hash_value[:8]  # 8-character anonymous ID
```

#### Data Generalization Rules
```python
generalization_rules = {
    'team_size': [
        (0, 5, 'micro'), 
        (6, 15, 'small'), 
        (16, 50, 'medium'), 
        (51, 200, 'large'), 
        (201, float('inf'), 'enterprise')
    ],
    'velocity': [
        (0, 2, 'slow'), 
        (2, 5, 'moderate'), 
        (5, 10, 'fast'), 
        (10, float('inf'), 'rapid')
    ]
}
```

### 4. Temporal Anonymization

#### Hour Bucketing
```python
def _anonymize_timestamp(self, timestamp: str) -> str:
    """Round timestamp to nearest hour"""
    dt = datetime.fromisoformat(timestamp)
    rounded = dt.replace(minute=0, second=0, microsecond=0)
    return rounded.isoformat()
```

## Consent Management Architecture

### 1. Consent Data Structure

```python
consent_data = {
    'failure_patterns': {
        'consent_level': 'basic',
        'granted_at': '2025-06-25T10:00:00',
        'version': '1.0',
        'explicit_consent': True,
        'conditions': ['review_annually']
    },
    'global': {
        'last_updated': '2025-06-25T10:00:00',
        'version': '1.0',
        'audit_trail': [
            {
                'action': 'consent_updated',
                'timestamp': '2025-06-25T10:00:00',
                'categories_changed': ['failure_patterns'],
                'version': '1.0'
            }
        ]
    }
}
```

### 2. Consent Levels

| Level | Description | Data Access |
|-------|-------------|-------------|
| `DENIED` | No consent given | No data collection |
| `BASIC` | Minimal data sharing | Anonymized patterns only |
| `ENHANCED` | Additional insights | More detailed anonymized data |
| `FULL` | Maximum benefit | All available anonymized insights |

### 3. Audit Trail Implementation

```python
def update_consent(self, consent_response: Dict[str, Any]) -> None:
    """Update consent with full audit trail"""
    timestamp = datetime.now()
    
    # Store consent decisions
    for category_name, decision in consent_response.get("categories", {}).items():
        self.consent_data[category_name] = {
            "consent_level": decision.get("level", ConsentLevel.DENIED.value),
            "granted_at": timestamp.isoformat(),
            "version": self.consent_version,
            "explicit_consent": True
        }
    
    # Add to audit trail
    self.consent_data["global"]["audit_trail"].append({
        "action": "consent_updated",
        "timestamp": timestamp.isoformat(),
        "categories_changed": list(consent_response.get("categories", {}).keys()),
        "version": self.consent_version
    })
```

## Data Subject Rights Implementation

### 1. Right to Access

```python
def exercise_data_right(self, right: DataSubjectRights, details: Dict[str, Any] = None) -> Dict[str, Any]:
    """Process data subject rights requests"""
    timestamp = datetime.now()
    request_id = f"dsr_{int(timestamp.timestamp())}_{right.value}"
    
    request_record = {
        "request_id": request_id,
        "right": right.value,
        "requested_at": timestamp.isoformat(),
        "details": details or {},
        "status": "submitted",
        "expected_completion": (timestamp + timedelta(days=30)).isoformat()
    }
    
    return {
        "request_id": request_id,
        "status": "submitted",
        "expected_completion": request_record["expected_completion"],
        "instructions": self._get_rights_instructions(right)
    }
```

### 2. Data Export Format

```python
def export_consent_data(self) -> Dict[str, Any]:
    """Export all consent data for portability rights"""
    return {
        "version": self.consent_version,
        "exported_at": datetime.now().isoformat(),
        "consent_data": self.consent_data,
        "explanations": self.category_explanations,
        "format_version": "1.0"
    }
```

## Security Implementation

### 1. Encryption

#### Key Management
```python
def _get_or_create_encryption_key(self) -> bytes:
    """Generate and manage encryption keys"""
    if 'encryption_key' in self.config:
        return self.config['encryption_key'].encode()
    
    # Create new encryption key using Fernet
    key = Fernet.generate_key()
    self.config['encryption_key'] = key.decode()
    self._save_config()
    
    return key
```

#### Data Encryption
```python
def _encrypt_payload(self, payload: Dict[str, Any]) -> str:
    """Encrypt transmission payload"""
    json_data = json.dumps(payload)
    encrypted_data = self.cipher.encrypt(json_data.encode())
    return encrypted_data.decode()
```

### 2. Secure Transmission

```python
async def _transmit_insights(self, force: bool = False) -> None:
    """Securely transmit anonymized insights"""
    payload = {
        'installation_id': self.installation_id,
        'timestamp': datetime.now().isoformat(),
        'insights': [insight.data for insight in self.pending_insights],
        'privacy_version': '1.0',
        'client_version': '1.0.0'
    }
    
    encrypted_payload = self._encrypt_payload(payload)
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            self.config['endpoint'],
            json={'data': encrypted_payload},
            headers={'Content-Type': 'application/json'},
            ssl=self._get_ssl_context(),
            timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            # Handle response...
```

## Privacy Validation

### 1. Anonymization Validation

```python
def validate_anonymization(self, original: StrategicInsight, anonymized: StrategicInsight) -> Dict[str, Any]:
    """Validate that anonymization preserved privacy"""
    validation_results = {
        'privacy_preserved': True,
        'utility_maintained': True,
        'issues': []
    }
    
    # Check for remaining identifiers in values
    def check_values_for_identifiers(obj, path=""):
        if isinstance(obj, str):
            # Allow hashed values (8-character strings)
            if len(obj) != 8 and any(keyword in obj.lower() for keyword in ['user', 'project', 'team']):
                validation_results['privacy_preserved'] = False
                validation_results['issues'].append(f'Potential identifier at {path}: {obj}')
    
    check_values_for_identifiers(anonymized.data)
    return validation_results
```

### 2. Privacy Budget Tracking

```python
class PrivacyBudgetTracker:
    def __init__(self, total_budget: float = 1.0):
        self.total_budget = total_budget
        self.used_budget = 0.0
        self.category_usage = {}
    
    def consume_budget(self, category: str, epsilon: float) -> bool:
        """Attempt to consume privacy budget"""
        if self.used_budget + epsilon > self.total_budget:
            return False
        
        self.used_budget += epsilon
        self.category_usage[category] = self.category_usage.get(category, 0) + epsilon
        return True
    
    def remaining_budget(self) -> float:
        """Get remaining privacy budget"""
        return self.total_budget - self.used_budget
```

## Configuration Management

### 1. Privacy-First Defaults

```python
DEFAULT_CONFIG = {
    'enabled': False,  # Opt-in only
    'consent': {},
    'auto_transmit': True,
    'transmission_interval': 86400,  # 24 hours
    'min_batch_size': 10,
    'max_queue_size': 1000,
    'privacy_level': 'maximum',
    'endpoint': 'https://telemetry.pm-agent.dev/v1/insights'
}
```

### 2. Privacy Level Settings

```python
PRIVACY_LEVELS = {
    'maximum': {
        'differential_privacy': True,
        'k_anonymity': 10,
        'temporal_buckets': 'hour',
        'identifier_hashing': True,
        'data_generalization': 'aggressive'
    },
    'balanced': {
        'differential_privacy': True,
        'k_anonymity': 5,
        'temporal_buckets': 'hour',
        'identifier_hashing': True,
        'data_generalization': 'moderate'
    },
    'minimal': {
        'differential_privacy': False,
        'k_anonymity': 3,
        'temporal_buckets': 'day',
        'identifier_hashing': True,
        'data_generalization': 'basic'
    }
}
```

## Testing Privacy Controls

### 1. Privacy Validation Tests

```python
def test_anonymization_validation(anonymizer, sample_insight):
    """Test anonymization validation detects privacy issues"""
    anonymized = anonymizer.anonymize_insight(sample_insight)
    validation = anonymizer.validate_anonymization(sample_insight, anonymized)
    
    assert validation['privacy_preserved'] is True
    assert validation['utility_maintained'] is True
    assert len([i for i in validation['issues'] if 'critical' in i.lower()]) == 0
```

### 2. Consent Management Tests

```python
def test_consent_granularity(consent_manager):
    """Test granular consent controls"""
    mixed_consent = {
        'categories': {
            InsightCategory.FAILURE_PREDICTION.value: {'level': ConsentLevel.BASIC.value},
            InsightCategory.TEAM_OPTIMIZATION.value: {'level': ConsentLevel.DENIED.value}
        }
    }
    
    consent_manager.update_consent(mixed_consent)
    
    assert consent_manager.has_consent_for(InsightCategory.FAILURE_PREDICTION) is True
    assert consent_manager.has_consent_for(InsightCategory.TEAM_OPTIMIZATION) is False
```

### 3. Differential Privacy Tests

```python
def test_differential_privacy_noise_addition(anonymizer):
    """Test that differential privacy noise is properly added"""
    original_value = 0.5
    
    # Generate multiple noisy values
    noisy_values = [
        anonymizer._add_differential_privacy_noise(original_value, 'confidence_score')
        for _ in range(100)
    ]
    
    # All values should be different due to noise
    assert len(set(noisy_values)) > 90  # Most should be unique
    
    # Mean should be close to original (unbiased)
    mean_value = sum(noisy_values) / len(noisy_values)
    assert abs(mean_value - original_value) < 0.1
```

## Compliance Checklist

### GDPR Compliance
- ✅ Lawful basis for processing (consent + legitimate interest)
- ✅ Data minimization (only necessary insights collected)
- ✅ Purpose limitation (clear purpose for each category)
- ✅ Storage limitation (anonymized data retention)
- ✅ Data subject rights implementation
- ✅ Privacy by design and by default
- ✅ Data protection impact assessment
- ✅ Consent management and withdrawal

### Privacy by Design Principles
- ✅ Proactive not reactive
- ✅ Privacy as the default setting
- ✅ Privacy embedded into design
- ✅ Full functionality (positive-sum)
- ✅ End-to-end security
- ✅ Visibility and transparency
- ✅ Respect for user privacy

## Monitoring and Auditing

### 1. Privacy Metrics

```python
class PrivacyMetrics:
    def __init__(self):
        self.anonymization_failures = 0
        self.consent_violations = 0
        self.budget_exhaustions = 0
        self.validation_failures = 0
    
    def log_anonymization_failure(self, category: str, reason: str):
        """Log anonymization failure for monitoring"""
        self.anonymization_failures += 1
        logger.error(f"Anonymization failed for {category}: {reason}")
    
    def log_consent_violation(self, category: str, action: str):
        """Log consent violation for compliance"""
        self.consent_violations += 1
        logger.warning(f"Consent violation: {action} attempted for {category}")
```

### 2. Audit Logging

```python
def audit_log(action: str, category: str = None, user_id: str = None, details: Dict = None):
    """Create audit log entry for compliance"""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'action': action,
        'category': category,
        'user_id': user_id,
        'details': details or {},
        'privacy_version': '1.0'
    }
    
    # Log to secure audit trail
    audit_logger.info(json.dumps(log_entry))
```

---

*This technical guide provides implementation details for privacy-preserving telemetry. For questions or clarifications, contact the development team.*