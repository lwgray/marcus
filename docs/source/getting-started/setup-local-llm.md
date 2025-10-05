# Setting Up Local LLM with Marcus

This guide shows you how to run Marcus with a local Large Language Model (LLM) for completely offline operation.

## Configuration Methods

Marcus supports two ways to configure local models:

1. **config_marcus.json** (Recommended)
2. **Environment variables** (Override config values)

## Recommended Models for Coding & Reasoning

For Marcus's task analysis and code understanding, these models work best:

### 🏆 Top Pick for Contributors

1. **Qwen2.5-Coder** ⭐ **(Highly Recommended - Best Free Coding Model)**
   - **Best for:** Complex software development, Marcus contribution
   - **Quality:** Rivals GPT-4 on coding benchmarks
   - **Sizes:** 1.5B, 7B, 14B, 32B
   - **Best balance:** `qwen2.5-coder:7b` (runs on 8GB RAM)
   - **Why choose this:** State-of-the-art code understanding, excellent instruction following
   - **Released:** Late 2024, specifically optimized for software engineering tasks

### Other Excellent Options

2. **DeepSeek-Coder** (Also Excellent)
   - Great for code understanding and generation
   - Sizes: 1.3B, 6.7B, 33B
   - Best balance: `deepseek-coder:6.7b`
   - Slightly older than Qwen2.5 but still very capable

3. **CodeLlama**
   - Meta's code-specialized model
   - Sizes: 7B, 13B, 34B
   - Best for Marcus: `codellama:13b`
   - Good for smaller tasks, fast responses

4. **Mixtral** (For advanced reasoning)
   - Strong general reasoning + code
   - Size: 8x7B (requires ~48GB RAM)
   - Use: `mixtral:8x7b`
   - Best for complex multi-step reasoning

5. **Mistral** (Lightweight option)
   - Good general purpose model
   - Size: 7B
   - Use: `mistral:7b`
   - Best for: Low-end hardware, fast iteration

## Quick Start with Ollama

### 1. Install Ollama

```bash
# macOS/Linux
curl -fsSL https://ollama.com/install.sh | sh

# Or download from: https://ollama.com/download
```

### 2. Pull a Model

```bash
# Best for Marcus development (recommended)
ollama pull qwen2.5-coder:7b

# Alternative: DeepSeek-Coder (also excellent)
ollama pull deepseek-coder:6.7b

# Alternative: CodeLlama
ollama pull codellama:13b

# For lighter systems (8GB RAM minimum)
ollama pull mistral:7b
```

### 3. Configure Marcus

#### Method 1: Using config_marcus.json (Recommended)

Update your `config_marcus.json`:

```json
{
  "ai": {
    "provider": "local",
    "enabled": true,
    "local_model": "qwen2.5-coder:7b",
    "local_url": "http://localhost:11434/v1",
    "local_key": "none"
  }
}
```

#### Method 2: Using Environment Variables

Environment variables override config values:

```bash
# Override the provider
export MARCUS_LLM_PROVIDER=local

# Override the model (use the best one)
export MARCUS_LOCAL_LLM_PATH=qwen2.5-coder:7b

# Override the URL (if not using default Ollama)
export MARCUS_LOCAL_LLM_URL=http://localhost:11434/v1

# Override the API key (if needed)
export MARCUS_LOCAL_LLM_KEY=your-key-here
```

### 4. Start Marcus

```bash
# Ollama starts automatically when you pull a model
# Just run Marcus normally
python -m marcus_mcp
```

## Complete Configuration Example

Here's a full `config_marcus.json` configured for local model usage:

```json
{
  "auto_find_board": false,
  "kanban": {
    "provider": "planka"
  },
  "planka": {
    "base_url": "http://localhost:3333",
    "email": "demo@demo.demo",
    "password": "demo"  # pragma: allowlist secret
  },
  "ai": {
    "provider": "local",
    "enabled": true,
    "local_model": "qwen2.5-coder:7b",
    "local_url": "http://localhost:11434/v1",
    "local_key": "none",
    "anthropic_api_key": "",
    "openai_api_key": "",
    "model": "claude-3-sonnet-20240229"
  },
  "features": {
    "events": true,
    "context": true,
    "memory": false,
    "visibility": false
  }
}
```

## Advanced Configuration

### Using Different Inference Servers

Marcus supports any OpenAI-compatible API. Configure in `config_marcus.json`:

```json
{
  "ai": {
    "provider": "local",
    "local_model": "your-model-name",
    "local_url": "http://localhost:8080/v1",
    "local_key": "your-api-key"
  }
}
```

Examples for different servers:
- **llama.cpp server**: `"local_url": "http://localhost:8080/v1"`
- **text-generation-webui**: `"local_url": "http://localhost:5000/v1"`
- **LocalAI**: `"local_url": "http://localhost:8080/v1"`

### Configuration Priority

Marcus uses this priority order:
1. Environment variables (highest priority)
2. config_marcus.json
3. Default values (lowest priority)

This allows you to:
- Set defaults in config_marcus.json
- Override temporarily with environment variables
- Test different models without changing config

### Performance Tuning

1. **Model Selection by RAM**:
   - 8GB RAM: Use 7B models (`mistral:7b`)
   - 16GB RAM: Use 13B models (`codellama:13b`)
   - 32GB+ RAM: Use 33B+ models (`deepseek-coder:33b`)

2. **Ollama Performance Settings**:
   ```bash
   # Increase context window
   export OLLAMA_NUM_CTX=8192

   # Use GPU acceleration (if available)
   export OLLAMA_CUDA_VISIBLE_DEVICES=0
   ```

3. **Timeout Configuration**:
   Local models can be slower. The LocalLLMProvider sets a 120-second timeout by default.

## Switching Between Local and Cloud Models

You can easily switch between providers:

### Temporary Switch (Environment Variable)
```bash
# Use local model
export MARCUS_LLM_PROVIDER=local

# Switch back to Anthropic
export MARCUS_LLM_PROVIDER=anthropic
```

### Permanent Switch (config_marcus.json)
```json
{
  "ai": {
    "provider": "anthropic",  // or "local" or "openai"
    // ... rest of config
  }
}
```

## Troubleshooting

### "Failed to connect to local LLM server"
- Check Ollama is running: `ollama list`
- Verify the model is downloaded: `ollama pull <model>`
- Check the URL: `curl http://localhost:11434/api/tags`

### "Local LLM API error: 404"
- Your Ollama might not have OpenAI compatibility
- The LocalLLMProvider will automatically fallback to Ollama's native API

### Slow Performance
- Use smaller models for faster response
- Enable GPU acceleration if available
- Reduce max tokens in config if needed

## Model Recommendations by Use Case

| Use Case | Recommended Model | Why |
|----------|------------------|-----|
| **Contributing to Marcus** | `qwen2.5-coder:7b` | **Best overall - state-of-the-art coding** |
| General Marcus usage | `qwen2.5-coder:7b` or `deepseek-coder:6.7b` | Excellent code understanding |
| Low-end hardware (8GB) | `mistral:7b` | Good balance of size/performance |
| High-end hardware (16GB+) | `qwen2.5-coder:14b` | Even better quality |
| Complex reasoning | `mixtral:8x7b` | Advanced reasoning (needs 48GB RAM) |
| Fast responses | `codellama:7b` | Smaller but still code-focused |

## Example Session

```bash
# 1. Install and setup
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5-coder:7b

# 2. Configure for local development
cp .env.dev.example .env
# Or update config_marcus.json: Set "provider": "local" and "local_model": "qwen2.5-coder:7b"

# 3. Use Marcus normally
python -m marcus_mcp

# Marcus will now use your local model for all AI operations!
# Zero API costs, excellent code quality ✨
```

## Benefits of Local Models

- **Privacy**: All data stays on your machine
- **No API Costs**: Unlimited usage
- **Offline Operation**: Works without internet
- **Customization**: Fine-tune models for your needs
- **Low Latency**: No network round trips

## Next Steps

- Try different models to find what works best for your workflow
- Consider fine-tuning a model on your codebase
- Adjust temperature settings for more/less creative responses
