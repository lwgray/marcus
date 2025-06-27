# Marcus AI Engine Setup

## Issue
The AI Engine was running in fallback mode because:
1. `ANTHROPIC_API_KEY` environment variable wasn't loaded
2. Incorrect model name was specified

## Solutions Applied

### 1. Environment Variable Loading
Updated `run_ui_server.py` to load the `.env` file:

```python
# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    env_file = project_root / '.env'
    if env_file.exists():
        load_dotenv(env_file)
        print(f"Loaded environment from {env_file}")
except ImportError:
    print("Warning: python-dotenv not installed, skipping .env file")
```

### 2. Fixed Model Name
Changed from:
```python
self.model: str = "claude-3-sonnet-20241022"
```

To:
```python
self.model: str = "claude-3-5-sonnet-20241022"
```

## Result
✅ AI Engine is now fully operational with:
- Anthropic client initialized successfully
- AI Engine connection verified
- Intelligent task assignment capabilities
- Blocker resolution with AI suggestions
- Risk analysis and mitigation

## Important for Experiments
When running Marcus or the UI server directly with Python (not through Docker), ensure:
1. The `.env` file exists with `ANTHROPIC_API_KEY` set
2. Use the correct startup commands that load environment variables
3. The model name matches available Claude models

## Verification
Check logs for:
```
✅ Anthropic client initialized successfully
✅ AI Engine connection verified
```

If you see "fallback mode" warnings, the AI features will still work but with simpler rule-based logic instead of Claude's intelligence.