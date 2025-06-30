# Configuration Migration Guide

Marcus configuration has been consolidated from multiple files into a single `marcus.config.json` file for simplicity and clarity.

## What Changed

### Before
- Configuration was split between:
  - `.env` file (API keys, provider settings)
  - `config_marcus.json` (project IDs, connection details)
  - Various environment variables
  - `config/marcus_config.json` (for Settings class)

### After
- All configuration is now in a single `marcus.config.json` file
- The file is organized into logical sections
- Sensitive data (API keys) are kept in the same secure file
- `marcus.config.json` is git-ignored for security

## Migration Steps

1. **Run the migration script** (if you haven't already):
   ```bash
   python scripts/migrate_config.py
   ```
   This will:
   - Create `marcus.config.json` from your existing `.env` and `config_marcus.json`
   - Back up your original files
   - Create `marcus.config.example.json` as a template

2. **Review the generated config**:
   ```bash
   cat marcus.config.json
   ```
   Ensure all your settings were migrated correctly.

3. **Delete old config files** (after confirming Marcus works):
   ```bash
   rm .env config_marcus.json
   ```

## Configuration Structure

The new `marcus.config.json` has these sections:

```json
{
  "kanban": {
    "provider": "planka",  // or "github", "linear"
    "planka": { /* Planka settings */ },
    "github": { /* GitHub settings */ },
    "linear": { /* Linear settings */ }
  },
  "ai": {
    "anthropic_api_key": "your-key",
    "model": "claude-3-sonnet-20241022",
    // Other AI settings
  },
  "monitoring": {
    "interval": 900,
    // Monitoring settings
  },
  "communication": {
    "slack_enabled": false,
    // Communication settings
  },
  "advanced": {
    "debug": false,
    "port": 8000
  }
}
```

## Environment Variable Overrides

For CI/CD or production deployments, you can still override any setting using environment variables:

- `MARCUS_KANBAN_PROVIDER=github`
- `MARCUS_AI_ANTHROPIC_API_KEY=sk-ant-xxx`
- `MARCUS_MONITORING_INTERVAL=600`

The pattern is: `MARCUS_<SECTION>_<KEY>` where nested keys use underscores.

## Troubleshooting

### "marcus.config.json not found" error
- Run `python scripts/migrate_config.py` to create it
- Or copy `marcus.config.example.json` to `marcus.config.json` and fill in your values

### Settings not loading correctly
- Ensure `marcus.config.json` is in the project root directory
- Check that the JSON is valid (no trailing commas, proper quotes)

### API keys not working
- Verify the `ai.anthropic_api_key` field has your actual key
- Check that quotes are correct in the JSON file

## Security Notes

- `marcus.config.json` contains sensitive data (API keys, passwords)
- It's automatically git-ignored to prevent accidental commits
- Never commit this file to version control
- Use `marcus.config.example.json` as a template for sharing