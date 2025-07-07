# Configuring Hybrid Dependency Inference

The hybrid dependency inference system uses configurable thresholds to balance accuracy, performance, and API costs. This guide explains how to tune these settings for your needs.

## Configuration Location

Add the `hybrid_inference` section to your `config_marcus.json`:

```json
{
  "hybrid_inference": {
    "pattern_confidence_threshold": 0.8,
    "ai_confidence_threshold": 0.7,
    "combined_confidence_boost": 0.15,
    "max_ai_pairs_per_batch": 20,
    "min_shared_keywords": 2,
    "enable_ai_inference": true,
    "cache_ttl_hours": 24,
    "require_component_match": true,
    "max_dependency_chain_length": 10
  }
}
```

## Configuration Options

### Core Thresholds

#### `pattern_confidence_threshold` (0.0-1.0, default: 0.8)
Pattern matches above this confidence level don't need AI validation.
- **Higher values (0.9+)**: More AI calls, better accuracy for edge cases
- **Lower values (0.7-)**: Fewer AI calls, may miss complex dependencies
- **Recommended**: 0.8 for most projects

#### `ai_confidence_threshold` (0.0-1.0, default: 0.7)
Minimum confidence required to accept an AI-inferred dependency.
- **Higher values (0.8+)**: More conservative, fewer false positives
- **Lower values (0.6-)**: More permissive, may include weak dependencies
- **Recommended**: 0.7 for balanced results

#### `combined_confidence_boost` (0.0-0.3, default: 0.15)
Confidence increase when pattern and AI agree on a dependency.
- **Higher values (0.2+)**: Strong preference for agreement
- **Lower values (0.1-)**: Less weight on agreement
- **Recommended**: 0.15 for moderate boost

### Performance Settings

#### `max_ai_pairs_per_batch` (1+, default: 20)
Maximum task pairs analyzed in one AI request.
- **Higher values (30+)**: Fewer API calls, longer prompts
- **Lower values (10-)**: More API calls, simpler analysis
- **Recommended**: 20 for balance

#### `min_shared_keywords` (1+, default: 2)
Minimum shared keywords for tasks to be considered related.
- **Higher values (3+)**: Fewer AI analyses, may miss subtle relationships
- **Lower values (1)**: More AI analyses, better coverage
- **Recommended**: 2 for most projects

### Cost Control

#### `enable_ai_inference` (true/false, default: true)
Master switch for AI-powered inference.
- **true**: Use hybrid approach (patterns + AI)
- **false**: Pattern-only mode (no API calls)

#### `cache_ttl_hours` (0+, default: 24)
How long to cache AI inference results.
- **Higher values (48+)**: Fewer repeat analyses
- **Lower values (0-12)**: More up-to-date analysis
- **Recommended**: 24 hours for daily development

## Preset Configurations

Use preset configurations for common scenarios:

```python
# In your code
from src.config.hybrid_inference_config import get_preset_config

# Conservative - High accuracy, more API calls
config = get_preset_config('conservative')

# Balanced - Default settings
config = get_preset_config('balanced')

# Aggressive - More dependencies found, higher costs
config = get_preset_config('aggressive')

# Cost Optimized - Minimize API calls
config = get_preset_config('cost_optimized')

# Pattern Only - No API calls
config = get_preset_config('pattern_only')
```

## Tuning Guide

### For a New Project
Start with **balanced** settings to understand your dependency patterns:
```json
{
  "pattern_confidence_threshold": 0.8,
  "ai_confidence_threshold": 0.7,
  "enable_ai_inference": true
}
```

### For Cost Optimization
Reduce API calls while maintaining quality:
```json
{
  "pattern_confidence_threshold": 0.85,
  "ai_confidence_threshold": 0.75,
  "max_ai_pairs_per_batch": 50,
  "cache_ttl_hours": 48,
  "min_shared_keywords": 3
}
```

### For Maximum Accuracy
When dependency correctness is critical:
```json
{
  "pattern_confidence_threshold": 0.9,
  "ai_confidence_threshold": 0.8,
  "combined_confidence_boost": 0.2,
  "max_ai_pairs_per_batch": 10,
  "min_shared_keywords": 1
}
```

### For CI/CD Environments
Disable AI to avoid API costs in automated environments:
```json
{
  "enable_ai_inference": false
}
```

## Monitoring API Usage

Track your API usage with these metrics:

1. **Pattern-only dependencies**: No API cost
2. **AI-analyzed pairs**: Each batch counts as one API call
3. **Cache hits**: Reused results don't cost API calls

Example log output:
```
Dependency Inference Statistics:
- Pattern matches: 15
- AI inferences: 3
- Final dependencies: 18
  - Both methods: 2
  - Pattern only: 13
  - AI only: 3
- Average confidence: 0.85
```

## Troubleshooting

### Too Many API Calls
- Increase `pattern_confidence_threshold` to 0.85-0.9
- Increase `min_shared_keywords` to 3
- Increase `cache_ttl_hours` to 48-72

### Missing Dependencies
- Decrease `pattern_confidence_threshold` to 0.7-0.75
- Decrease `ai_confidence_threshold` to 0.6-0.65
- Decrease `min_shared_keywords` to 1

### False Positives
- Increase `ai_confidence_threshold` to 0.8-0.85
- Enable `require_component_match`
- Review and adjust pattern rules

## Best Practices

1. **Start Conservative**: Begin with higher thresholds and reduce as needed
2. **Monitor Costs**: Track API usage in your first week
3. **Cache Wisely**: Longer cache for stable projects, shorter for rapid development
4. **Review Results**: Periodically check inferred dependencies for accuracy
5. **Use Presets**: Start with a preset and fine-tune from there