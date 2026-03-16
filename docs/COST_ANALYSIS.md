# Marcus Token Cost Analysis

**Last Updated**: 2025-01-11
**Purpose**: Understand AI costs and explore local model alternatives for Marcus development

---

## Executive Summary

**Good News**: Marcus is already configured to use **Claude 3 Haiku** (the cheapest Claude model) by default. You can also use **free local models** via Ollama for zero cost.

**Estimated Cost to Develop Marcus Itself**:
- Using Claude 3 Haiku: ~$5-15 per major feature
- Using local Ollama models: **$0** (free, but slower)

---

## Where Marcus Uses AI

### 1. Project Creation (create_project MCP tool)
**Operations**:
- Parse natural language → tasks (1 AI call)
- Generate task descriptions (N AI calls, parallelized)
- Generate subtasks (N AI calls, parallelized)

**Token Estimate Per Project**:
- Input: ~500-1000 tokens (project description + context)
- Output: ~2000-4000 tokens (tasks + descriptions)
- **Total**: ~2500-5000 tokens per project

### 2. Task Operations
**Operations**:
- Semantic task analysis
- Dependency inference
- Task description enhancement
- Effort estimation
- Blocker analysis

**Token Estimate Per Task**:
- Input: ~300-600 tokens
- Output: ~500-1000 tokens
- **Total**: ~800-1600 tokens per task

### 3. Post-Project Analysis (Phase 3)
**Operations** (5 analysis phases):
- Requirement divergence analysis
- Decision impact tracing
- Instruction quality assessment
- Failure diagnosis
- Task redundancy detection

**Token Estimate Per Analysis**:
- Small project (10 tasks): ~20,000 tokens
- Medium project (50 tasks): ~100,000 tokens
- Large project (200 tasks): ~400,000 tokens

---

## Cost Breakdown by Provider

### Current Default: Claude 3 Haiku (Cheapest)

**Pricing** (as of January 2025):
- Input: $0.25 per million tokens
- Output: $1.25 per million tokens

**Costs**:
```
Project Creation (5,000 tokens):
- Input (1,000):  $0.00025
- Output (4,000): $0.005
- Total: ~$0.005 per project

Task Operations (1,600 tokens per task):
- Input (600):   $0.00015
- Output (1,000): $0.00125
- Total: ~$0.0014 per task

Post-Project Analysis (100,000 tokens, medium project):
- Input (30,000):  $0.0075
- Output (70,000): $0.0875
- Total: ~$0.095 per analysis
```

**Developing Marcus Itself** (rough estimate):
- Create 10 test projects: $0.05
- Process 100 tasks: $0.14
- Run 5 analyses: $0.48
- **Total**: ~$0.67 per day of active development

**Monthly estimate** (20 working days): ~$13.40

### Alternative: Claude 3.5 Sonnet (Better Quality)

**Pricing**:
- Input: $3 per million tokens
- Output: $15 per million tokens

**Costs**:
```
Project Creation: ~$0.064 per project
Task Operations: ~$0.017 per task
Post-Project Analysis: ~$1.35 per medium project
```

**Monthly estimate** (20 working days): ~$160

### Alternative: Local Models (Ollama) - FREE

**Supported Models**:
- Llama 3 (8B, 70B)
- Mistral (7B)
- CodeLlama
- Qwen 2.5

**Costs**: $0 (electricity only)

**Trade-offs**:
- ✅ **Free** - no API costs
- ✅ **Privacy** - data stays local
- ✅ **No rate limits**
- ❌ **Slower** - especially for large models
- ❌ **Lower quality** - compared to Claude/GPT-4
- ❌ **Requires GPU** - for acceptable performance

---

## Configuration Options

Marcus supports **three providers** via `config_marcus.json`:

### Option 1: Claude 3 Haiku (Default - Cheapest Cloud Option)

```json
{
  "ai": {
    "provider": "anthropic",
    "model": "claude-3-haiku-20240307",
    "anthropic_api_key": "sk-ant-..."  // pragma: allowlist secret
  }
}
```

**When to use**: Balanced cost/quality for development

### Option 2: Claude 3.5 Sonnet (Higher Quality)

```json
{
  "ai": {
    "provider": "anthropic",
    "model": "claude-3-5-sonnet-20241022",
    "anthropic_api_key": "sk-ant-..."  // pragma: allowlist secret
  }
}
```

**When to use**: Need better reasoning for complex projects

### Option 3: Local Ollama (Free)

```json
{
  "ai": {
    "provider": "ollama",
    "model": "llama3:8b",
    "ollama_base_url": "http://localhost:11434"
  }
}
```

**Setup**:
```bash
# Install Ollama
brew install ollama  # macOS
# or download from https://ollama.com

# Start Ollama service
ollama serve

# Pull a model
ollama pull llama3:8b
```

**When to use**:
- Budget constraints
- Privacy concerns
- High-volume testing

---

## Cost Optimization Strategies

### 1. Hybrid Approach (Recommended)
Use different models for different operations:

```json
{
  "ai": {
    "provider": "anthropic",
    "model": "claude-3-haiku-20240307",  // Default
    "analysis": {
      "model": "claude-3-5-sonnet-20241022"  // Better for analysis
    }
  }
}
```

**Savings**: 70-80% cost reduction while maintaining quality where it matters

### 2. Local Development, Cloud Production
- Use Ollama (free) during development/testing
- Use Claude Haiku for production demos
- Use Claude Sonnet for customer projects

### 3. Cache Results
Marcus already caches AI results in:
- Project history (`~/.marcus/projects/{project_id}/`)
- Analysis results (reusable across projects)

---

## Recommendations for Marcus Development

### For Daily Development (You):

**Best Option**: **Ollama (Llama 3 8B)**
- Cost: $0
- Speed: 2-5 seconds per call (with GPU)
- Quality: Good enough for development/testing

**Setup**:
```bash
# Install and start Ollama
brew install ollama
ollama serve

# Pull Llama 3
ollama pull llama3:8b

# Update config_marcus.json
{
  "ai": {
    "provider": "ollama",
    "model": "llama3:8b"
  }
}
```

### For Production/Demos:

**Best Option**: **Claude 3 Haiku**
- Cost: ~$13/month for active development
- Speed: 1-2 seconds per call
- Quality: Production-ready

### For Research/Complex Analysis:

**Best Option**: **Claude 3.5 Sonnet**
- Cost: ~$160/month for active development
- Speed: 2-3 seconds per call
- Quality: Best reasoning capabilities

---

## Token Usage Monitoring

Marcus includes **token tracking** in `/src/cost_tracking/`:

```python
from src.cost_tracking.token_tracker import TokenTracker

tracker = TokenTracker()
result = await tracker.track_usage(
    operation="project_creation",
    model="claude-3-haiku",
    input_tokens=1000,
    output_tokens=4000
)
print(f"Cost: ${result.cost:.4f}")
```

**Check your usage**:
```bash
# View usage logs
cat ~/.marcus/logs/token_usage.log

# Summary by operation
python -m src.cost_tracking.report
```

---

## Frequently Asked Questions

### Q: Can I mix providers?
**A**: Yes! Marcus supports fallback providers. If Anthropic fails, it auto-falls back to OpenAI or Ollama.

### Q: How much will it cost to use Marcus in production?
**A**: Depends on scale:
- **Solo developer** (10 projects/month): ~$1-5/month (Haiku)
- **Small team** (50 projects/month): ~$5-25/month (Haiku)
- **Enterprise** (500 projects/month): ~$50-250/month (Haiku)

### Q: Is Ollama good enough?
**A**: For development: **Yes**
For production: **Depends** - Llama 3 70B rivals Claude 3 Haiku, but requires beefy GPU

### Q: What about GPT-4?
**A**: Supported via OpenAI provider, but more expensive than Claude Sonnet. Configure in `ai.provider: "openai"`.

---

## Summary Table

| Provider | Model | Input Cost | Output Cost | Quality | Speed | Monthly Est.* |
|----------|-------|------------|-------------|---------|-------|---------------|
| **Ollama** | Llama 3 8B | $0 | $0 | ⭐⭐⭐ | 🐢 | **$0** |
| **Anthropic** | Claude 3 Haiku | $0.25/M | $1.25/M | ⭐⭐⭐⭐ | ⚡⚡ | **$13** |
| **Anthropic** | Claude 3.5 Sonnet | $3/M | $15/M | ⭐⭐⭐⭐⭐ | ⚡ | **$160** |
| **OpenAI** | GPT-4 | $5/M | $15/M | ⭐⭐⭐⭐⭐ | ⚡ | **$200** |

\* *Active development (20 days/month)*

---

## Next Steps

1. **Try Ollama first**: Zero cost, good for learning Marcus
2. **Get Anthropic API key**: For production demos ($5 credit on signup)
3. **Monitor usage**: Check `~/.marcus/logs/token_usage.log`
4. **Optimize**: Use Haiku for routine tasks, Sonnet for complex analysis

**Ready to get started?**
```bash
# Free option (Ollama)
brew install ollama
ollama serve
ollama pull llama3:8b

# Paid option (Anthropic)
export ANTHROPIC_API_KEY="sk-ant-..."  # pragma: allowlist secret
```
