# Marcus Configuration Audit

**Date**: 2025-12-20
**Purpose**: Document existing scattered configuration before Week 1 consolidation
**Issue**: #68 - Configuration Centralization

---

## Executive Summary

Marcus currently has **FOUR different configuration systems** operating simultaneously:

1. **`config_loader.py`** - Loads `config_marcus.json`, handles env vars, migrations
2. **`settings.py`** - Separate Settings class with different defaults
3. **`hybrid_inference_config.py`** - Dataclass for hybrid inference settings
4. **Direct `os.getenv()` calls** - Scattered across 14+ files

This creates:
- ❌ **Confusion**: Which config system to use?
- ❌ **Duplication**: Same settings defined in multiple places
- ❌ **Inconsistency**: Different default values across systems
- ❌ **No validation**: Hard to know what's required vs optional
- ❌ **Deployment pain**: Users don't know how to configure Marcus

---

## Current Configuration Files

### 1. Primary Config Files

| File | Purpose | Status |
|------|---------|--------|
| `config_marcus.json` | User's actual config (gitignored) | ✅ Active |
| `config_marcus.json.example` | User template | ✅ Active |
| `config_marcus.local.example.json` | Alternative template | ❓ Unclear purpose |
| `config/test_config.json` | Test config | ✅ For tests |
| `config/pm_agent_config.json` | PM agent specific | ❓ Unclear purpose |

### 2. Configuration Loading Systems

#### System 1: ConfigLoader (`src/config/config_loader.py`)

**What it does:**
- Singleton pattern
- Loads `config_marcus.json` from multiple locations
- Handles environment variable overrides (82 env vars mapped!)
- Migrates legacy configs to multi-project format
- Provides dot-notation access (`config.get("ai.model")`)

**Key methods:**
```python
get_config() -> ConfigLoader
get("path.to.value", default)
get_kanban_config()
get_ai_config()
get_monitoring_config()
get_hybrid_inference_config()
```

**Environment variables it handles:**
```bash
# 30+ environment variables, including:
MARCUS_CONFIG
MARCUS_KANBAN_PROVIDER
MARCUS_KANBAN_PLANKA_BASE_URL
MARCUS_KANBAN_PLANKA_EMAIL
MARCUS_KANBAN_PLANKA_PASSWORD
MARCUS_KANBAN_GITHUB_TOKEN
MARCUS_AI_ANTHROPIC_API_KEY
MARCUS_AI_OPENAI_API_KEY
MARCUS_AI_MODEL
MARCUS_LLM_PROVIDER
MARCUS_LOCAL_LLM_PATH
MARCUS_LOCAL_LLM_URL
MARCUS_MONITORING_INTERVAL
MARCUS_SLACK_ENABLED
# ... and many more
```

#### System 2: Settings (`src/config/settings.py`)

**What it does:**
- Class-based configuration
- Has its own defaults (different from config_loader!)
- Calls `get_config()` but then has own env var overrides
- Provides specialized getters

**Defaults (DIFFERENT from config_loader!):**
```python
{
  "monitoring_interval": 900,  # 15 minutes
  "stall_threshold_hours": 24,
  "ai_settings": {
    "model": "claude-3-sonnet-20241022",  # Different model!
    "temperature": 0.7,
    "max_tokens": 2000
  },
  "features": {
    "enable_subtasks": True
  }
}
```

**Environment variables it ALSO handles:**
```bash
MARCUS_MONITORING_INTERVAL  # Duplicate!
MARCUS_SLACK_ENABLED        # Duplicate!
ANTHROPIC_API_KEY           # Duplicate!
MARCUS_ENABLE_SUBTASKS      # Different name than config_loader!
```

#### System 3: HybridInferenceConfig (`src/config/hybrid_inference_config.py`)

**What it does:**
- Dataclass for dependency inference settings
- Type-safe configuration
- Validation method
- THIS IS WHAT WE WANT FOR ALL CONFIG!

```python
@dataclass
class HybridInferenceConfig:
    pattern_confidence_threshold: float = 0.8
    ai_confidence_threshold: float = 0.7
    # ... etc

    def validate(self) -> None:
        # Clear validation errors
```

**This is the RIGHT pattern** - we need to extend this to ALL configuration!

---

## Scattered `os.getenv()` Calls

### Files with Direct Environment Variable Access

Found **30 `os.getenv()` calls** and **20 `os.environ[]` accesses** across **14 files**:

#### AI Providers
- `src/ai/core/ai_engine.py`
  - `MARCUS_AI_ENABLED`
- `src/ai/providers/anthropic_provider.py`
  - `ANTHROPIC_API_KEY` (gets from config OR env)
- `src/ai/providers/openai_provider.py`
  - `OPENAI_API_KEY`
  - `OPENAI_MODEL`
- `src/ai/providers/local_provider.py`
  - `MARCUS_LOCAL_LLM_URL`
  - `MARCUS_LOCAL_LLM_KEY`
- `src/ai/providers/llm_abstraction.py`
  - `ANTHROPIC_API_KEY`
  - `OPENAI_API_KEY`
  - `MARCUS_LOCAL_LLM_PATH`

#### Kanban Integration
- `src/integrations/kanban_factory.py`
  - `LINEAR_API_KEY`
  - `LINEAR_TEAM_ID`
  - `LINEAR_PROJECT_ID`
  - `GITHUB_TOKEN`
  - `GITHUB_OWNER`
  - `GITHUB_REPO`
  - `GITHUB_PROJECT_NUMBER`
  - `KANBAN_PROVIDER`
- `src/integrations/kanban_client.py`
  - `KANBAN_MCP_PATH`
- `src/integrations/providers/planka.py`
  - `PLANKA_BASE_URL`
  - `PLANKA_AGENT_EMAIL`

#### MCP Server
- `src/marcus_mcp/server.py`
  - Sets environment variables! (anti-pattern)
  - `PLANKA_BASE_URL`
  - `PLANKA_AGENT_EMAIL`
  - `PLANKA_AGENT_PASSWORD`
  - `PLANKA_PROJECT_NAME`
  - `GITHUB_TOKEN`
  - `GITHUB_OWNER`
  - `GITHUB_REPO`
  - `LINEAR_API_KEY`
  - `LINEAR_TEAM_ID`
  - `PYTHONUNBUFFERED`

#### Tools
- `src/marcus_mcp/tools/task.py`
  - `GITHUB_OWNER`
  - `GITHUB_REPO`

#### Configuration
- `src/config/config_loader.py`
  - `MARCUS_CONFIG` (expected - finds config file)
  - Plus 30+ in `_apply_env_overrides()`
- `src/config/settings.py`
  - `MARCUS_CONFIG`
  - `MARCUS_MONITORING_INTERVAL`
  - `MARCUS_SLACK_ENABLED`
  - `SLACK_WEBHOOK_URL`
  - `MARCUS_EMAIL_ENABLED`
  - `ANTHROPIC_API_KEY`
  - `MARCUS_ENABLE_SUBTASKS`

#### Other
- `src/enhancements/configurable_pm_agent.py`
  - `MARCUS_PROJECT_ID`
  - `MARCUS_BOARD_ID`

---

## Problems Identified

### 1. Duplicate Environment Variable Handling

Same env vars handled in multiple places with different logic:

```python
# In config_loader.py:
"MARCUS_AI_ANTHROPIC_API_KEY" -> "ai.anthropic_api_key"

# In settings.py:
"ANTHROPIC_API_KEY" -> config["anthropic_api_key"]

# In anthropic_provider.py:
os.getenv("ANTHROPIC_API_KEY")

# In llm_abstraction.py:
os.getenv("ANTHROPIC_API_KEY")
```

**Result**: Same variable checked 4 different ways!

### 2. Inconsistent Defaults

Different default values in different systems:

| Setting | config_marcus.json.example | settings.py | Actual Code |
|---------|---------------------------|-------------|-------------|
| AI Model | `claude-3-sonnet-20240229` | `claude-3-sonnet-20241022` | `claude-3-haiku-20240307` (in some files) |
| Temperature | Not specified | `0.7` | Varies |
| Monitoring Interval | Not in example | `900` (15 min) | Unknown |

### 3. No Single Source of Truth

To find out what model Marcus uses, you need to check:
1. `config_marcus.json` (if it exists)
2. `MARCUS_AI_MODEL` env var (checked by config_loader)
3. settings.py defaults
4. Hard-coded values in provider files

### 4. Missing Validation

- No validation on startup
- Errors happen at runtime when config is wrong
- User doesn't know what's required vs optional
- No clear error messages ("API key missing" vs "KeyError: api_key")

### 5. Anti-Patterns

**MCP Server SETS environment variables** (src/marcus_mcp/server.py):
```python
os.environ["PLANKA_BASE_URL"] = planka_config.get("base_url", "")
os.environ["PLANKA_AGENT_EMAIL"] = planka_config.get("email", "")
```

This is backwards! Environment should override config, not vice versa.

---

## What Week 1 Will Fix

### Before (Current State)

**User perspective:**
- "How do I configure Marcus?" → Unclear
- "What do I need to set?" → Unknown
- "Where do environment variables go?" → Confusing
- "Why isn't my API key working?" → No validation errors

**Developer perspective:**
```python
# Where do I get the API key?
# Option 1:
config_loader = get_config()
key = config_loader.get("ai.anthropic_api_key")

# Option 2:
settings = Settings()
key = settings.get("anthropic_api_key")

# Option 3:
key = os.getenv("ANTHROPIC_API_KEY")

# Option 4:
from src.config.config_loader import get_anthropic_api_key
key = get_anthropic_api_key()

# Which is right? ALL OF THEM ARE USED!
```

### After (Week 1 Centralized Config)

**User perspective:**
- "How do I configure Marcus?" → Copy `config_marcus.example.json`, fill in values
- "What do I need to set?" → Clear validation tells you at startup
- "Where do environment variables go?" → `${ENV_VAR}` syntax in config file
- "Why isn't my API key working?" → "Anthropic API key not set in config.ai.anthropic_api_key"

**Developer perspective:**
```python
# Single way to get config:
from src.config.marcus_config import get_config

config = get_config()
api_key = config.ai.anthropic_api_key
planka_url = config.kanban.planka_base_url
model = config.ai.model
temperature = config.ai.temperature

# Type-safe, autocomplete works, clear structure
```

---

## Configuration Schema (Current `config_marcus.json`)

Based on `config_marcus.json.example` and code analysis:

```json
{
  // Legacy fields (should be removed)
  "project_id": "XXXXX",
  "board_id": "XXXXX",
  "project_name": "PROJECT_NAME",

  // Top-level settings
  "auto_find_board": false,

  // Kanban provider selection
  "kanban": {
    "provider": "planka"  // or "github" or "linear"
  },

  // Planka credentials
  "planka": {
    "base_url": "http://localhost:3333",
    "email": "demo@demo.demo",
    "password": "demo"  // pragma: allowlist secret
  },

  // AI settings
  "ai": {
    "anthropic_api_key": "sk-ant-XX",  // pragma: allowlist secret
    "model": "claude-3-sonnet-20240229",
    // Missing: openai_api_key, temperature, max_tokens, enabled
  },

  // GitHub settings
  "github": {
    "token": "",
    "owner": "",
    "repo": ""
    // Missing: project_number
  },

  // Linear settings
  "linear": {
    "api_key": "",
    "team_id": ""
    // Missing: project_id
  },

  // Feature flags
  "features": {
    "events": false,
    "context": false,
    "memory": false,
    "visibility": false
    // Missing: enable_subtasks (in settings.py)
  },

  // Hybrid inference (already well-defined!)
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

  // MISSING SECTIONS:
  // - monitoring (in settings.py)
  // - communication (in settings.py)
  // - escalation (in settings.py)
  // - team_config (in settings.py)
  // - performance (in settings.py)
  // - mcp (MCP server settings)
  // - transport (HTTP/STDIO settings)
  // - task_lease (from config_loader mentions)
  // - board_health (mentioned in code)
}
```

---

## Recommendations for Week 1

### 1. Keep What Works

✅ **`hybrid_inference_config.py` pattern**
- Dataclass structure is excellent
- Validation method is exactly what we need
- Extend this pattern to all configuration

✅ **`config_loader.py` env var mapping**
- The env var override system is comprehensive
- Keep the `${ENV_VAR}` substitution
- Keep the dot-notation access

✅ **Existing `config_marcus.json.example`**
- Users already have this
- Keep backward compatibility

### 2. Consolidate

🔄 **Merge Settings and ConfigLoader**
- Single MarcusConfig dataclass
- Merge all defaults into one place
- Single validation method
- Single env var override system

🔄 **Remove Duplicate Systems**
- Remove Settings class (merge into MarcusConfig)
- Remove direct `os.getenv()` calls
- All config access goes through `get_config()`

### 3. Add Missing Pieces

➕ **Complete schema**
- Document EVERY setting
- Add missing sections (monitoring, communication, etc.)
- Clear required vs optional

➕ **Validation**
- Validate on startup
- Clear error messages
- Guide users to fix issues

➕ **Type safety**
- Dataclasses for all config sections
- IDE autocomplete
- Catch errors at dev time

---

## Migration Path (Week 1 Plan)

### Monday: Data Structure
- Create `src/config/marcus_config.py`
- Dataclasses for all sections (like hybrid_inference_config.py)
- Merge defaults from Settings and config_loader

### Tuesday: Validation
- Add `validate()` method
- Environment variable override support
- Test all validation cases

### Wednesday: Migration
- Update all 14 files to use `get_config()`
- Remove direct `os.getenv()` calls
- Remove Settings class
- Fix MCP server anti-pattern

### Thursday: Documentation
- Update `config_marcus.example.json` with ALL options
- Add comments explaining each setting
- Create `docs/CONFIGURATION.md` guide

### Friday: Testing
- Backward compatibility tests
- Full regression testing
- Integration tests
- Ready for PR

---

## Success Metrics

After Week 1, we should have:

✅ **Single config file** - `config_marcus.json`
✅ **Single config class** - `MarcusConfig`
✅ **Single import** - `from src.config.marcus_config import get_config`
✅ **Clear validation** - Errors on startup with helpful messages
✅ **Type safety** - Dataclasses with type hints
✅ **Documentation** - Every setting explained
✅ **Backward compatible** - Existing configs still work
✅ **Easy deployment** - Copy example, fill in, done

---

## Appendix: Full Environment Variable List

Current environment variables found in code (needs consolidation):

```bash
# Configuration file location
MARCUS_CONFIG

# AI - Anthropic
ANTHROPIC_API_KEY
MARCUS_AI_ANTHROPIC_API_KEY  # Duplicate!

# AI - OpenAI
OPENAI_API_KEY
MARCUS_AI_OPENAI_API_KEY  # Duplicate!
OPENAI_MODEL

# AI - Local
MARCUS_LOCAL_LLM_PATH
MARCUS_LOCAL_LLM_URL
MARCUS_LOCAL_LLM_KEY

# AI - General
MARCUS_AI_MODEL
MARCUS_LLM_PROVIDER
MARCUS_AI_ENABLED

# Kanban - Provider
KANBAN_PROVIDER
MARCUS_KANBAN_PROVIDER  # Duplicate!

# Kanban - Planka
PLANKA_BASE_URL
MARCUS_KANBAN_PLANKA_BASE_URL  # Duplicate!
PLANKA_AGENT_EMAIL
MARCUS_KANBAN_PLANKA_EMAIL  # Duplicate!
PLANKA_AGENT_PASSWORD
MARCUS_KANBAN_PLANKA_PASSWORD  # Duplicate!
MARCUS_KANBAN_PLANKA_PROJECT_ID
MARCUS_KANBAN_PLANKA_BOARD_ID

# Kanban - GitHub
GITHUB_TOKEN
MARCUS_KANBAN_GITHUB_TOKEN  # Duplicate!
GITHUB_OWNER
MARCUS_KANBAN_GITHUB_OWNER  # Duplicate!
GITHUB_REPO
MARCUS_KANBAN_GITHUB_REPO  # Duplicate!
GITHUB_PROJECT_NUMBER

# Kanban - Linear
LINEAR_API_KEY
MARCUS_KANBAN_LINEAR_API_KEY  # Duplicate!
LINEAR_TEAM_ID
MARCUS_KANBAN_LINEAR_TEAM_ID  # Duplicate!
LINEAR_PROJECT_ID

# Kanban - MCP
KANBAN_MCP_PATH

# Monitoring
MARCUS_MONITORING_INTERVAL

# Communication
MARCUS_SLACK_ENABLED
SLACK_WEBHOOK_URL
MARCUS_SLACK_WEBHOOK_URL
MARCUS_EMAIL_ENABLED

# Features
MARCUS_ENABLE_SUBTASKS

# Advanced
MARCUS_DEBUG
MARCUS_PORT
PYTHONUNBUFFERED

# Legacy/Unknown
MARCUS_PROJECT_ID
MARCUS_BOARD_ID
```

**Total: ~50 environment variables (many duplicates!)**

After Week 1: Standardize on one naming convention, remove duplicates.
