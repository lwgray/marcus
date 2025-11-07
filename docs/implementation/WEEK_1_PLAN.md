## Week 1: Configuration & Foundation

**Goal**: Centralize configuration management to enable easy deployment and packaging.

**Why**: Currently, configuration is scattered across environment variables, hard-coded values, and inconsistent config loading. This makes deployment difficult and confuses new users. Solving this first unblocks all other work.

**Related Issue**: #68 (CRITICAL)

---

### Monday: Create Configuration Data Structure

**What**: Build `src/config/marcus_config.py` with type-safe configuration classes.

**Why**: Dataclasses provide:
- Type safety (catch errors at development time)
- Clear documentation (every field has a type)
- Easy validation (we'll add validation methods)
- IDE autocomplete (developers know what config exists)

**How**:

#### Step 1.1: Create the config module directory
```bash
mkdir -p src/config
touch src/config/__init__.py
touch src/config/marcus_config.py
```

#### Step 1.2: Define configuration dataclasses

Create `src/config/marcus_config.py`:

```python
"""
Centralized configuration for Marcus.

This module provides type-safe configuration management with:
- Dataclass-based structure for type safety
- Environment variable override support
- Validation on startup
- Clear defaults

Example:
    from src.config.marcus_config import get_config

    config = get_config()
    api_key = config.ai.anthropic_api_key
    planka_url = config.kanban.planka_url
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class MCPSettings:
    """
    MCP (Model Context Protocol) related configuration.

    Attributes
    ----------
    kanban_client_path : str
        Path to kanban-mcp client (default: ~/dev/kanban-mcp/dist/index.js)
    timeout : int
        Timeout for MCP operations in seconds (default: 30)
    retry_attempts : int
        Number of retry attempts for failed operations (default: 3)
    """
    kanban_client_path: str = "~/dev/kanban-mcp/dist/index.js"
    timeout: int = 30
    retry_attempts: int = 3


@dataclass
class AISettings:
    """
    AI provider configuration.

    Attributes
    ----------
    provider : str
        AI provider to use: "anthropic", "openai", or "local"
    anthropic_api_key : Optional[str]
        Anthropic API key (required if provider="anthropic")
    openai_api_key : Optional[str]
        OpenAI API key (required if provider="openai")
    model : Optional[str]
        Model name (e.g., "claude-3-haiku-20240307")
    temperature : float
        Temperature for LLM sampling (0.0-1.0)
    max_tokens : int
        Maximum tokens for LLM responses
    enabled : bool
        Whether AI features are enabled
    """
    provider: str = "anthropic"
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    model: Optional[str] = "claude-3-haiku-20240307"
    temperature: float = 0.7
    max_tokens: int = 4096
    enabled: bool = True


@dataclass
class KanbanSettings:
    """
    Kanban provider configuration.

    Attributes
    ----------
    provider : str
        Kanban provider: "planka", "github", or "linear"
    board_name : Optional[str]
        Default board name to use
    planka_base_url : Optional[str]
        Planka server URL (required if provider="planka")
    planka_email : Optional[str]
        Planka user email (required if provider="planka")
    planka_password : Optional[str]
        Planka user password (required if provider="planka")
    github_token : Optional[str]
        GitHub personal access token (required if provider="github")
    github_owner : Optional[str]
        GitHub repository owner
    github_repo : Optional[str]
        GitHub repository name
    linear_api_key : Optional[str]
        Linear API key (required if provider="linear")
    linear_team_id : Optional[str]
        Linear team ID
    """
    provider: str = "planka"
    board_name: Optional[str] = None
    planka_base_url: Optional[str] = None
    planka_email: Optional[str] = None
    planka_password: Optional[str] = None
    github_token: Optional[str] = None
    github_owner: Optional[str] = None
    github_repo: Optional[str] = None
    linear_api_key: Optional[str] = None
    linear_team_id: Optional[str] = None


@dataclass
class FeaturesSettings:
    """
    Feature flags for optional Marcus features.

    Attributes
    ----------
    events : bool
        Enable event logging
    context : bool
        Enable context system
    memory : bool
        Enable memory/learning system
    visibility : bool
        Enable visibility features
    """
    events: bool = True
    context: bool = True
    memory: bool = True
    visibility: bool = False


@dataclass
class HybridInferenceSettings:
    """
    Configuration for hybrid dependency inference.

    Attributes
    ----------
    pattern_confidence_threshold : float
        Minimum confidence for pattern-based inference (0.0-1.0)
    ai_confidence_threshold : float
        Minimum confidence for AI-based inference (0.0-1.0)
    combined_confidence_boost : float
        Boost when both methods agree (0.0-1.0)
    max_ai_pairs_per_batch : int
        Maximum task pairs to send to AI per batch
    min_shared_keywords : int
        Minimum shared keywords for pattern matching
    enable_ai_inference : bool
        Whether to use AI for dependency inference
    cache_ttl_hours : int
        Cache time-to-live in hours
    require_component_match : bool
        Require component names to match for dependencies
    max_dependency_chain_length : int
        Maximum allowed dependency chain length
    """
    pattern_confidence_threshold: float = 0.8
    ai_confidence_threshold: float = 0.7
    combined_confidence_boost: float = 0.15
    max_ai_pairs_per_batch: int = 20
    min_shared_keywords: int = 2
    enable_ai_inference: bool = True
    cache_ttl_hours: int = 24
    require_component_match: bool = True
    max_dependency_chain_length: int = 10


@dataclass
class TaskLeaseSettings:
    """
    Configuration for task lease management.

    Attributes
    ----------
    default_hours : float
        Default lease duration in hours
    max_renewals : int
        Maximum number of lease renewals
    warning_hours : float
        Hours before expiry to send warning
    grace_period_minutes : int
        Grace period after expiry before reclaiming task
    renewal_decay_factor : float
        Factor to reduce lease time on each renewal
    min_lease_hours : float
        Minimum lease duration
    max_lease_hours : float
        Maximum lease duration
    stuck_threshold_renewals : int
        Number of renewals before task is considered stuck
    enable_adaptive : bool
        Enable adaptive lease durations based on task complexity
    priority_multipliers : Dict[str, float]
        Lease duration multipliers by priority
    complexity_multipliers : Dict[str, float]
        Lease duration multipliers by complexity
    """
    default_hours: float = 2.0
    max_renewals: int = 10
    warning_hours: float = 0.5
    grace_period_minutes: int = 30
    renewal_decay_factor: float = 0.9
    min_lease_hours: float = 1.0
    max_lease_hours: float = 24.0
    stuck_threshold_renewals: int = 5
    enable_adaptive: bool = True
    priority_multipliers: Dict[str, float] = field(default_factory=lambda: {
        "critical": 0.5,
        "high": 0.75,
        "medium": 1.0,
        "low": 1.5
    })
    complexity_multipliers: Dict[str, float] = field(default_factory=lambda: {
        "simple": 0.5,
        "complex": 1.5,
        "research": 2.0,
        "epic": 3.0
    })


@dataclass
class BoardHealthSettings:
    """
    Configuration for board health monitoring.

    Attributes
    ----------
    stale_task_days : int
        Days before a task is considered stale
    max_tasks_per_agent : int
        Maximum tasks an agent can have assigned
    """
    stale_task_days: int = 7
    max_tasks_per_agent: int = 3


@dataclass
class TransportSettings:
    """
    MCP transport configuration.

    Attributes
    ----------
    type : str
        Transport type: "http" or "stdio"
    http_host : str
        HTTP server host
    http_port : int
        HTTP server port
    http_path : str
        HTTP endpoint path
    log_level : str
        Logging level
    """
    type: str = "http"
    http_host: str = "0.0.0.0"
    http_port: int = 4298
    http_path: str = "/mcp"
    log_level: str = "info"


@dataclass
class MultiEndpointSettings:
    """
    Configuration for multiple MCP endpoints (human, agent, analytics).

    Attributes
    ----------
    human_enabled : bool
        Enable human endpoint
    human_port : int
        Human endpoint port
    human_host : str
        Human endpoint host
    human_path : str
        Human endpoint path
    agent_enabled : bool
        Enable agent endpoint
    agent_port : int
        Agent endpoint port
    agent_host : str
        Agent endpoint host
    agent_path : str
        Agent endpoint path
    analytics_enabled : bool
        Enable analytics endpoint
    analytics_port : int
        Analytics endpoint port
    analytics_host : str
        Analytics endpoint host
    analytics_path : str
        Analytics endpoint path
    """
    human_enabled: bool = True
    human_port: int = 4298
    human_host: str = "127.0.0.1"
    human_path: str = "/mcp"

    agent_enabled: bool = True
    agent_port: int = 4299
    agent_host: str = "127.0.0.1"
    agent_path: str = "/mcp"

    analytics_enabled: bool = True
    analytics_port: int = 4300
    analytics_host: str = "127.0.0.1"
    analytics_path: str = "/mcp"


@dataclass
class MarcusConfig:
    """
    Central configuration for Marcus.

    This is the main configuration class that contains all settings.
    Load it once at startup and use throughout the application.

    Attributes
    ----------
    mcp : MCPSettings
        MCP-related settings
    ai : AISettings
        AI provider settings
    kanban : KanbanSettings
        Kanban provider settings
    features : FeaturesSettings
        Feature flags
    hybrid_inference : HybridInferenceSettings
        Dependency inference settings
    task_lease : TaskLeaseSettings
        Task lease management settings
    board_health : BoardHealthSettings
        Board health monitoring settings
    transport : TransportSettings
        MCP transport settings
    multi_endpoint : MultiEndpointSettings
        Multi-endpoint configuration
    auto_find_board : bool
        Automatically find board by name
    single_project_mode : bool
        Run in single project mode
    log_level : str
        Global logging level
    data_dir : str
        Data directory path
    cache_dir : str
        Cache directory path
    """
    mcp: MCPSettings = field(default_factory=MCPSettings)
    ai: AISettings = field(default_factory=AISettings)
    kanban: KanbanSettings = field(default_factory=KanbanSettings)
    features: FeaturesSettings = field(default_factory=FeaturesSettings)
    hybrid_inference: HybridInferenceSettings = field(default_factory=HybridInferenceSettings)
    task_lease: TaskLeaseSettings = field(default_factory=TaskLeaseSettings)
    board_health: BoardHealthSettings = field(default_factory=BoardHealthSettings)
    transport: TransportSettings = field(default_factory=TransportSettings)
    multi_endpoint: MultiEndpointSettings = field(default_factory=MultiEndpointSettings)

    # Global settings
    auto_find_board: bool = False
    single_project_mode: bool = True
    log_level: str = "INFO"
    data_dir: str = "~/.marcus/data"
    cache_dir: str = "~/.marcus/cache"

    @classmethod
    def from_file(cls, path: str = "config_marcus.json") -> "MarcusConfig":
        """
        Load configuration from JSON file.

        This method:
        1. Looks for config file at given path
        2. If not found, returns default configuration
        3. Parses JSON and creates nested dataclass instances
        4. Supports ${ENV_VAR} substitution in values

        Parameters
        ----------
        path : str
            Path to config file (default: "config_marcus.json")

        Returns
        -------
        MarcusConfig
            Loaded configuration

        Example
        -------
        >>> config = MarcusConfig.from_file("config_marcus.json")
        >>> print(config.ai.provider)
        "anthropic"
        """
        config_path = Path(path).expanduser()

        # If config file doesn't exist, return defaults
        if not config_path.exists():
            print(f"Warning: Config file not found at {config_path}, using defaults")
            return cls()

        # Load JSON
        with open(config_path) as f:
            data = json.load(f)

        # Substitute environment variables
        data = cls._substitute_env_vars(data)

        # Create nested configs
        return cls._from_dict(data)

    @classmethod
    def _substitute_env_vars(cls, data: Any) -> Any:
        """
        Recursively substitute ${ENV_VAR} with environment variable values.

        Example:
            "${ANTHROPIC_API_KEY}" -> actual API key from environment
        """
        if isinstance(data, dict):
            return {k: cls._substitute_env_vars(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [cls._substitute_env_vars(item) for item in data]
        elif isinstance(data, str) and data.startswith("${") and data.endswith("}"):
            # Extract env var name: "${VAR_NAME}" -> "VAR_NAME"
            env_var = data[2:-1]
            return os.getenv(env_var, data)  # Return original if not found
        else:
            return data

    @classmethod
    def _from_dict(cls, data: Dict[str, Any]) -> "MarcusConfig":
        """
        Create MarcusConfig from dictionary.

        Handles nested dataclasses by recursively creating them.
        """
        # Create nested configs
        nested_configs = {}

        if "mcp" in data:
            nested_configs["mcp"] = MCPSettings(**data["mcp"])

        if "ai" in data:
            nested_configs["ai"] = AISettings(**data["ai"])

        if "kanban" in data:
            nested_configs["kanban"] = KanbanSettings(**data["kanban"])

        # Handle old "planka" key for backward compatibility
        if "planka" in data:
            planka_data = data["planka"]
            if "kanban" not in nested_configs:
                nested_configs["kanban"] = KanbanSettings()
            nested_configs["kanban"].planka_base_url = planka_data.get("base_url")
            nested_configs["kanban"].planka_email = planka_data.get("email")
            nested_configs["kanban"].planka_password = planka_data.get("password")

        if "github" in data:
            github_data = data["github"]
            if "kanban" not in nested_configs:
                nested_configs["kanban"] = KanbanSettings()
            nested_configs["kanban"].github_token = github_data.get("token")
            nested_configs["kanban"].github_owner = github_data.get("owner")
            nested_configs["kanban"].github_repo = github_data.get("repo")

        if "linear" in data:
            linear_data = data["linear"]
            if "kanban" not in nested_configs:
                nested_configs["kanban"] = KanbanSettings()
            nested_configs["kanban"].linear_api_key = linear_data.get("api_key")
            nested_configs["kanban"].linear_team_id = linear_data.get("team_id")

        if "features" in data:
            nested_configs["features"] = FeaturesSettings(**data["features"])

        if "hybrid_inference" in data:
            nested_configs["hybrid_inference"] = HybridInferenceSettings(**data["hybrid_inference"])

        if "task_lease" in data:
            nested_configs["task_lease"] = TaskLeaseSettings(**data["task_lease"])

        if "board_health" in data:
            nested_configs["board_health"] = BoardHealthSettings(**data["board_health"])

        if "transport" in data:
            transport_data = data["transport"]
            nested_configs["transport"] = TransportSettings(
                type=transport_data.get("type", "http"),
                http_host=transport_data.get("http", {}).get("host", "0.0.0.0"),
                http_port=transport_data.get("http", {}).get("port", 4298),
                http_path=transport_data.get("http", {}).get("path", "/mcp"),
                log_level=transport_data.get("http", {}).get("log_level", "info")
            )

        if "multi_endpoint" in data:
            me_data = data["multi_endpoint"]
            nested_configs["multi_endpoint"] = MultiEndpointSettings(
                human_enabled=me_data.get("human", {}).get("enabled", True),
                human_port=me_data.get("human", {}).get("port", 4298),
                human_host=me_data.get("human", {}).get("host", "127.0.0.1"),
                human_path=me_data.get("human", {}).get("path", "/mcp"),

                agent_enabled=me_data.get("agent", {}).get("enabled", True),
                agent_port=me_data.get("agent", {}).get("port", 4299),
                agent_host=me_data.get("agent", {}).get("host", "127.0.0.1"),
                agent_path=me_data.get("agent", {}).get("path", "/mcp"),

                analytics_enabled=me_data.get("analytics", {}).get("enabled", True),
                analytics_port=me_data.get("analytics", {}).get("port", 4300),
                analytics_host=me_data.get("analytics", {}).get("host", "127.0.0.1"),
                analytics_path=me_data.get("analytics", {}).get("path", "/mcp")
            )

        # Extract top-level settings
        top_level = {
            "auto_find_board": data.get("auto_find_board", False),
            "single_project_mode": data.get("single_project_mode", True),
            "log_level": data.get("log_level", "INFO"),
            "data_dir": data.get("data_dir", "~/.marcus/data"),
            "cache_dir": data.get("cache_dir", "~/.marcus/cache")
        }

        # Combine nested and top-level
        return cls(**nested_configs, **top_level)


# Global config instance
_config: Optional[MarcusConfig] = None


def get_config() -> MarcusConfig:
    """
    Get or create global config instance.

    This function:
    1. Checks if config is already loaded
    2. If not, loads from config_marcus.json
    3. Validates configuration
    4. Returns config instance

    This should be called ONCE at application startup,
    then the result is reused throughout the application.

    Returns
    -------
    MarcusConfig
        The global configuration instance

    Raises
    ------
    ValueError
        If configuration validation fails

    Example
    -------
    >>> from src.config.marcus_config import get_config
    >>> config = get_config()
    >>> api_key = config.ai.anthropic_api_key
    """
    global _config
    if _config is None:
        # Try to load from MARCUS_CONFIG env var, else default
        config_path = os.getenv("MARCUS_CONFIG", "config_marcus.json")
        _config = MarcusConfig.from_file(config_path)
        _config.validate()
    return _config


def reload_config() -> MarcusConfig:
    """
    Force reload configuration from file.

    Useful for:
    - Testing (reset config between tests)
    - Hot-reloading config changes

    Returns
    -------
    MarcusConfig
        The reloaded configuration

    Example
    -------
    >>> config = reload_config()  # Force fresh load from disk
    """
    global _config
    config_path = os.getenv("MARCUS_CONFIG", "config_marcus.json")
    _config = MarcusConfig.from_file(config_path)
    _config.validate()
    return _config
```

#### Step 1.3: Write a test to verify it loads

Create `tests/unit/config/test_marcus_config.py`:

```python
"""
Unit tests for configuration loading.
"""

import json
import os
from pathlib import Path

import pytest

from src.config.marcus_config import (
    AISettings,
    KanbanSettings,
    MarcusConfig,
    get_config,
    reload_config,
)


class TestMarcusConfig:
    """Test suite for MarcusConfig"""

    def test_default_config_creation(self):
        """Test that default config can be created."""
        config = MarcusConfig()

        assert config.ai.provider == "anthropic"
        assert config.kanban.provider == "planka"
        assert config.features.events is True
        assert config.log_level == "INFO"

    def test_load_config_from_file(self, tmp_path):
        """Test loading config from JSON file."""
        # Create test config
        config_file = tmp_path / "test_config.json"
        config_data = {
            "ai": {
                "provider": "openai",
                "openai_api_key": "test-key-123",
                "temperature": 0.5
            },
            "kanban": {
                "provider": "github",
                "board_name": "Test Board"
            },
            "log_level": "DEBUG"
        }

        with open(config_file, "w") as f:
            json.dump(config_data, f)

        # Load config
        config = MarcusConfig.from_file(str(config_file))

        # Verify
        assert config.ai.provider == "openai"
        assert config.ai.openai_api_key == "test-key-123"
        assert config.ai.temperature == 0.5
        assert config.kanban.provider == "github"
        assert config.kanban.board_name == "Test Board"
        assert config.log_level == "DEBUG"

    def test_env_var_substitution(self, tmp_path, monkeypatch):
        """Test that ${ENV_VAR} syntax works."""
        # Set environment variable
        monkeypatch.setenv("TEST_API_KEY", "secret-key-from-env")

        # Create config with env var reference
        config_file = tmp_path / "test_config.json"
        config_data = {
            "ai": {
                "provider": "anthropic",
                "anthropic_api_key": "${TEST_API_KEY}"
            }
        }

        with open(config_file, "w") as f:
            json.dump(config_data, f)

        # Load config
        config = MarcusConfig.from_file(str(config_file))

        # Verify env var was substituted
        assert config.ai.anthropic_api_key == "secret-key-from-env"

    def test_backward_compatibility_planka(self, tmp_path):
        """Test that old 'planka' config key still works."""
        config_file = tmp_path / "test_config.json"
        config_data = {
            "planka": {
                "base_url": "http://localhost:3333",
                "email": "test@test.com",
                "password": "testpass"
            }
        }

        with open(config_file, "w") as f:
            json.dump(config_data, f)

        config = MarcusConfig.from_file(str(config_file))

        # Should map to kanban.planka_* fields
        assert config.kanban.planka_base_url == "http://localhost:3333"
        assert config.kanban.planka_email == "test@test.com"
        assert config.kanban.planka_password == "testpass"

    def test_nonexistent_config_returns_defaults(self, tmp_path):
        """Test that missing config file returns defaults."""
        nonexistent_file = tmp_path / "does_not_exist.json"

        config = MarcusConfig.from_file(str(nonexistent_file))

        # Should return default config
        assert config.ai.provider == "anthropic"
        assert config.kanban.provider == "planka"
```

Run the test:
```bash
pytest tests/unit/config/test_marcus_config.py -v
```

**Success Criteria**:
- ✅ All tests pass
- ✅ Config loads from file
- ✅ Environment variable substitution works
- ✅ Backward compatibility maintained

---

### Tuesday: Add Validation & Environment Overrides

**What**: Add validation methods to catch configuration errors at startup, plus environment variable override support.

**Why**:
- **Validation**: Catch errors early (missing API keys, invalid URLs) instead of runtime failures
- **Env overrides**: Allow Docker/CI environments to override config without editing files

**How**:

#### Step 2.1: Add validation method to MarcusConfig

Add to `src/config/marcus_config.py`:

```python
class MarcusConfig:
    # ... existing code ...

    def validate(self) -> None:
        """
        Validate configuration settings.

        Raises clear error messages for invalid configuration,
        making it easy for users to fix issues.

        Validation checks:
        - AI provider has required API keys
        - Kanban provider has required credentials
        - Ports are valid (1-65535)
        - Paths exist or can be created

        Raises
        ------
        ValueError
            If configuration is invalid, with detailed message

        Example
        -------
        >>> config = MarcusConfig.from_file("config.json")
        >>> config.validate()  # Raises ValueError if invalid
        """
        errors: List[str] = []

        # Validate AI settings
        if self.ai.enabled:
            if self.ai.provider == "anthropic":
                if not self.ai.anthropic_api_key:
                    errors.append(
                        "AI provider is 'anthropic' but anthropic_api_key is not set. "
                        "Set it in config_marcus.json or environment variable ANTHROPIC_API_KEY"
                    )
            elif self.ai.provider == "openai":
                if not self.ai.openai_api_key:
                    errors.append(
                        "AI provider is 'openai' but openai_api_key is not set. "
                        "Set it in config_marcus.json or environment variable OPENAI_API_KEY"
                    )

            # Validate temperature
            if not 0.0 <= self.ai.temperature <= 1.0:
                errors.append(f"AI temperature must be between 0.0 and 1.0, got {self.ai.temperature}")

        # Validate Kanban settings
        if self.kanban.provider == "planka":
            if not self.kanban.planka_base_url:
                errors.append(
                    "Kanban provider is 'planka' but planka_base_url is not set"
                )
            if not self.kanban.planka_email:
                errors.append(
                    "Kanban provider is 'planka' but planka_email is not set"
                )
            if not self.kanban.planka_password:
                errors.append(
                    "Kanban provider is 'planka' but planka_password is not set"
                )
        elif self.kanban.provider == "github":
            if not self.kanban.github_token:
                errors.append(
                    "Kanban provider is 'github' but github_token is not set"
                )
            if not self.kanban.github_owner or not self.kanban.github_repo:
                errors.append(
                    "Kanban provider is 'github' but github_owner or github_repo is not set"
                )
        elif self.kanban.provider == "linear":
            if not self.kanban.linear_api_key:
                errors.append(
                    "Kanban provider is 'linear' but linear_api_key is not set"
                )

        # Validate transport settings
        if self.transport.http_port < 1 or self.transport.http_port > 65535:
            errors.append(
                f"Transport HTTP port must be between 1-65535, got {self.transport.http_port}"
            )

        # Validate multi-endpoint ports don't conflict
        ports = [
            ("human", self.multi_endpoint.human_port),
            ("agent", self.multi_endpoint.agent_port),
            ("analytics", self.multi_endpoint.analytics_port),
        ]
        port_values = [p[1] for p in ports if p[1]]
        if len(port_values) != len(set(port_values)):
            errors.append(
                f"Multi-endpoint ports must be unique. Got: {dict(ports)}"
            )

        # Validate lease settings
        if self.task_lease.min_lease_hours > self.task_lease.max_lease_hours:
            errors.append(
                f"task_lease.min_lease_hours ({self.task_lease.min_lease_hours}) "
                f"cannot be greater than max_lease_hours ({self.task_lease.max_lease_hours})"
            )

        # Validate directories can be created
        for dir_name, dir_path in [("data_dir", self.data_dir), ("cache_dir", self.cache_dir)]:
            try:
                path = Path(dir_path).expanduser()
                path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(
                    f"Cannot create {dir_name} at {dir_path}: {e}"
                )

        # If there are errors, raise with clear message
        if errors:
            error_message = "Configuration validation failed:\n\n"
            for i, error in enumerate(errors, 1):
                error_message += f"{i}. {error}\n"
            error_message += "\nPlease fix these issues in config_marcus.json"
            raise ValueError(error_message)

    @classmethod
    def from_env(cls) -> "MarcusConfig":
        """
        Create configuration from environment variables only.

        Useful for Docker/CI environments where file-based config
        isn't convenient.

        Environment variable mapping:
        - ANTHROPIC_API_KEY -> ai.anthropic_api_key
        - OPENAI_API_KEY -> ai.openai_api_key
        - PLANKA_BASE_URL -> kanban.planka_base_url
        - PLANKA_AGENT_EMAIL -> kanban.planka_email
        - PLANKA_AGENT_PASSWORD -> kanban.planka_password
        - GITHUB_TOKEN -> kanban.github_token
        - GITHUB_OWNER -> kanban.github_owner
        - GITHUB_REPO -> kanban.github_repo
        - MARCUS_LOG_LEVEL -> log_level
        - MARCUS_AI_PROVIDER -> ai.provider
        - MARCUS_KANBAN_PROVIDER -> kanban.provider

        Returns
        -------
        MarcusConfig
            Configuration built from environment variables

        Example
        -------
        >>> # In Docker: export ANTHROPIC_API_KEY=sk-...
        >>> config = MarcusConfig.from_env()
        >>> print(config.ai.anthropic_api_key)
        "sk-..."
        """
        config = cls()

        # AI settings
        if api_key := os.getenv("ANTHROPIC_API_KEY"):
            config.ai.anthropic_api_key = api_key
        if api_key := os.getenv("OPENAI_API_KEY"):
            config.ai.openai_api_key = api_key
        if provider := os.getenv("MARCUS_AI_PROVIDER"):
            config.ai.provider = provider
        if model := os.getenv("MARCUS_AI_MODEL"):
            config.ai.model = model

        # Kanban settings
        if provider := os.getenv("MARCUS_KANBAN_PROVIDER"):
            config.kanban.provider = provider
        if url := os.getenv("PLANKA_BASE_URL"):
            config.kanban.planka_base_url = url
        if email := os.getenv("PLANKA_AGENT_EMAIL"):
            config.kanban.planka_email = email
        if password := os.getenv("PLANKA_AGENT_PASSWORD"):
            config.kanban.planka_password = password
        if token := os.getenv("GITHUB_TOKEN"):
            config.kanban.github_token = token
        if owner := os.getenv("GITHUB_OWNER"):
            config.kanban.github_owner = owner
        if repo := os.getenv("GITHUB_REPO"):
            config.kanban.github_repo = repo

        # Global settings
        if log_level := os.getenv("MARCUS_LOG_LEVEL"):
            config.log_level = log_level

        return config
```

#### Step 2.2: Update get_config() to try file first, fall back to env

Update `get_config()` in `src/config/marcus_config.py`:

```python
def get_config() -> MarcusConfig:
    """
    Get or create global config instance.

    Loading order:
    1. Try config file (config_marcus.json or MARCUS_CONFIG env var)
    2. If file not found, load from environment variables
    3. Validate configuration

    Returns
    -------
    MarcusConfig
        The global configuration instance

    Raises
    ------
    ValueError
        If configuration validation fails
    """
    global _config
    if _config is None:
        # Try to load from file first
        config_path = os.getenv("MARCUS_CONFIG", "config_marcus.json")

        if Path(config_path).exists():
            print(f"Loading configuration from {config_path}")
            _config = MarcusConfig.from_file(config_path)
        else:
            print(f"Config file {config_path} not found, loading from environment variables")
            _config = MarcusConfig.from_env()

        # Validate
        try:
            _config.validate()
            print("✓ Configuration validated successfully")
        except ValueError as e:
            print(f"✗ Configuration validation failed:\n{e}")
            raise

    return _config
```

#### Step 2.3: Add validation tests

Add to `tests/unit/config/test_marcus_config.py`:

```python
class TestConfigValidation:
    """Test configuration validation"""

    def test_validation_catches_missing_anthropic_key(self, tmp_path):
        """Test that missing Anthropic API key is caught."""
        config_file = tmp_path / "test_config.json"
        config_data = {
            "ai": {
                "provider": "anthropic",
                "enabled": True
                # Missing: anthropic_api_key
            }
        }

        with open(config_file, "w") as f:
            json.dump(config_data, f)

        config = MarcusConfig.from_file(str(config_file))

        with pytest.raises(ValueError) as exc_info:
            config.validate()

        assert "anthropic_api_key is not set" in str(exc_info.value)

    def test_validation_catches_missing_planka_credentials(self, tmp_path):
        """Test that missing Planka credentials are caught."""
        config_file = tmp_path / "test_config.json"
        config_data = {
            "kanban": {
                "provider": "planka"
                # Missing: planka_base_url, planka_email, planka_password
            }
        }

        with open(config_file, "w") as f:
            json.dump(config_data, f)

        config = MarcusConfig.from_file(str(config_file))

        with pytest.raises(ValueError) as exc_info:
            config.validate()

        error_msg = str(exc_info.value)
        assert "planka_base_url is not set" in error_msg
        assert "planka_email is not set" in error_msg

    def test_validation_catches_invalid_temperature(self, tmp_path):
        """Test that invalid AI temperature is caught."""
        config_file = tmp_path / "test_config.json"
        config_data = {
            "ai": {
                "provider": "anthropic",
                "anthropic_api_key": "test-key",
                "temperature": 1.5  # Invalid: must be 0.0-1.0
            }
        }

        with open(config_file, "w") as f:
            json.dump(config_data, f)

        config = MarcusConfig.from_file(str(config_file))

        with pytest.raises(ValueError) as exc_info:
            config.validate()

        assert "temperature must be between 0.0 and 1.0" in str(exc_info.value)

    def test_validation_catches_port_conflicts(self, tmp_path):
        """Test that duplicate ports in multi-endpoint are caught."""
        config_file = tmp_path / "test_config.json"
        config_data = {
            "multi_endpoint": {
                "human": {"port": 4298},
                "agent": {"port": 4298},  # Duplicate!
                "analytics": {"port": 4300}
            }
        }

        with open(config_file, "w") as f:
            json.dump(config_data, f)

        config = MarcusConfig.from_file(str(config_file))

        with pytest.raises(ValueError) as exc_info:
            config.validate()

        assert "ports must be unique" in str(exc_info.value).lower()

    def test_validation_passes_for_valid_config(self, tmp_path):
        """Test that valid config passes validation."""
        config_file = tmp_path / "test_config.json"
        config_data = {
            "ai": {
                "provider": "anthropic",
                "anthropic_api_key": "sk-test-key-123",
                "enabled": True
            },
            "kanban": {
                "provider": "planka",
                "planka_base_url": "http://localhost:3333",
                "planka_email": "test@test.com",
                "planka_password": "testpass"
            }
        }

        with open(config_file, "w") as f:
            json.dump(config_data, f)

        config = MarcusConfig.from_file(str(config_file))

        # Should not raise
        config.validate()


class TestEnvironmentOverrides:
    """Test environment variable overrides"""

    def test_from_env_creates_config(self, monkeypatch):
        """Test creating config from environment variables."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-env-key")
        monkeypatch.setenv("PLANKA_BASE_URL", "http://planka:1337")
        monkeypatch.setenv("PLANKA_AGENT_EMAIL", "env@test.com")
        monkeypatch.setenv("PLANKA_AGENT_PASSWORD", "envpass")
        monkeypatch.setenv("MARCUS_LOG_LEVEL", "DEBUG")

        config = MarcusConfig.from_env()

        assert config.ai.anthropic_api_key == "sk-env-key"
        assert config.kanban.planka_base_url == "http://planka:1337"
        assert config.kanban.planka_email == "env@test.com"
        assert config.kanban.planka_password == "envpass"
        assert config.log_level == "DEBUG"
```

Run tests:
```bash
pytest tests/unit/config/test_marcus_config.py -v
```

**Success Criteria**:
- ✅ Validation catches all error cases
- ✅ Validation passes for valid config
- ✅ Environment variable loading works
- ✅ All tests pass

---

### Wednesday: Migrate Existing Code to Use Centralized Config

**What**: Update all existing code to use `get_config()` instead of hard-coded values or scattered env vars.

**Why**:
- Single source of truth
- Easier to test (mock config)
- Easier to change settings (one place)
- Clearer what configuration exists

**How**:

#### Step 3.1: Find all hard-coded configuration

```bash
# Search for common patterns
grep -r "os.getenv" src/ | grep -v "config/marcus_config.py"
grep -r "ANTHROPIC_API_KEY" src/ | grep -v "config/"
grep -r "PLANKA" src/ | grep -v "config/"
grep -r "localhost:3333" src/
```

Make a list of files that need updating.

#### Step 3.2: Update MCP server initialization

Update `src/marcus_mcp/server.py`:

```python
# OLD CODE (find and replace):
# self.api_key = os.getenv("ANTHROPIC_API_KEY")
# self.planka_url = os.getenv("PLANKA_BASE_URL", "http://localhost:3333")

# NEW CODE:
from src.config.marcus_config import get_config

class MarcusServer:
    def __init__(self):
        # Load configuration
        self.config = get_config()

        # Use config throughout
        self.api_key = self.config.ai.anthropic_api_key
        self.planka_url = self.config.kanban.planka_base_url

        # ... rest of initialization
```

#### Step 3.3: Update AI engine

Update `src/ai/llm_abstraction.py`:

```python
# OLD:
# api_key = os.getenv("ANTHROPIC_API_KEY")
# model = os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307")

# NEW:
from src.config.marcus_config import get_config

class LLMAbstraction:
    def __init__(self):
        config = get_config()

        if config.ai.provider == "anthropic":
            self.client = Anthropic(api_key=config.ai.anthropic_api_key)
            self.model = config.ai.model or "claude-3-haiku-20240307"
        elif config.ai.provider == "openai":
            self.client = OpenAI(api_key=config.ai.openai_api_key)
            self.model = config.ai.model or "gpt-4"

        self.temperature = config.ai.temperature
        self.max_tokens = config.ai.max_tokens
```

#### Step 3.4: Update Kanban client initialization

Update `src/integrations/planka/planka_client.py`:

```python
# OLD:
# base_url = os.getenv("PLANKA_BASE_URL")
# email = os.getenv("PLANKA_AGENT_EMAIL")
# password = os.getenv("PLANKA_AGENT_PASSWORD")

# NEW:
from src.config.marcus_config import get_config

class PlankaClient:
    def __init__(self):
        config = get_config()

        self.base_url = config.kanban.planka_base_url
        self.email = config.kanban.planka_email
        self.password = config.kanban.planka_password

        # Validate we have what we need
        if not all([self.base_url, self.email, self.password]):
            raise ValueError(
                "Planka credentials not configured. "
                "Check config_marcus.json or environment variables."
            )
```

#### Step 3.5: Update feature flags

Update code using feature flags:

```python
# OLD:
# if os.getenv("MARCUS_ENABLE_MEMORY") == "true":

# NEW:
from src.config.marcus_config import get_config

config = get_config()
if config.features.memory:
    # Memory features enabled
    pass
```

#### Step 3.6: Create migration testing script

Create `scripts/test_config_migration.sh`:

```bash
#!/bin/bash
#
# Test that configuration migration works
#

set -e

echo "Testing configuration migration..."

# Test 1: Server starts with config file
echo "1. Testing server startup with config file..."
python -c "
from src.config.marcus_config import get_config
config = get_config()
print(f'✓ Config loaded: AI provider={config.ai.provider}')
"

# Test 2: Validation catches errors
echo "2. Testing validation catches missing API key..."
python -c "
from src.config.marcus_config import MarcusConfig
config = MarcusConfig()
config.ai.enabled = True
config.ai.provider = 'anthropic'
config.ai.anthropic_api_key = None
try:
    config.validate()
    print('✗ Validation should have failed')
    exit(1)
except ValueError as e:
    print('✓ Validation correctly caught missing API key')
"

# Test 3: Environment variables work
echo "3. Testing environment variable overrides..."
export ANTHROPIC_API_KEY="test-key-from-env"
python -c "
from src.config.marcus_config import MarcusConfig
config = MarcusConfig.from_env()
assert config.ai.anthropic_api_key == 'test-key-from-env'
print('✓ Environment variables work')
"

echo "All configuration tests passed!"
```

Make it executable:
```bash
chmod +x scripts/test_config_migration.sh
```

Run it:
```bash
./scripts/test_config_migration.sh
```

**Success Criteria**:
- ✅ All hard-coded values migrated
- ✅ Server starts successfully
- ✅ No import errors
- ✅ Tests pass

---

### Thursday: Create config_marcus.example.json

**What**: Create user-facing configuration template with comments explaining every option.

**Why**:
- New users don't know what configuration options exist
- Comments provide inline documentation
- Example values show the expected format
- Makes it easy to get started

**How**:

#### Step 4.1: Create comprehensive example file

Create `config_marcus.example.json`:

```json
{
  "_comment_1": "Marcus Configuration File",
  "_comment_2": "Copy this file to config_marcus.json and fill in your values",
  "_comment_3": "You can use ${ENV_VAR} syntax to reference environment variables",

  "auto_find_board": false,
  "_comment_auto_find_board": "If true, Marcus will search for board by name. If false, you must specify board_id.",

  "single_project_mode": true,
  "_comment_single_project_mode": "If true, Marcus works on one project at a time. Set false for multi-project orchestration.",

  "kanban": {
    "provider": "planka",
    "_comment_provider": "Kanban provider: 'planka', 'github', or 'linear'",

    "board_name": "My Project Board",
    "_comment_board_name": "Default board name to use (optional if auto_find_board is false)",

    "planka_base_url": "http://localhost:3333",
    "_comment_planka_base_url": "(Planka only) URL to your Planka server",

    "planka_email": "demo@demo.demo",
    "_comment_planka_email": "(Planka only) Agent email for authentication",

    "planka_password": "${PLANKA_AGENT_PASSWORD}",
    "_comment_planka_password": "(Planka only) Agent password. Use ${ENV_VAR} for security!",

    "github_token": "${GITHUB_TOKEN}",
    "_comment_github_token": "(GitHub only) Personal access token with repo scope",

    "github_owner": "",
    "_comment_github_owner": "(GitHub only) Repository owner (username or org)",

    "github_repo": "",
    "_comment_github_repo": "(GitHub only) Repository name",

    "linear_api_key": "${LINEAR_API_KEY}",
    "_comment_linear_api_key": "(Linear only) API key from Linear settings",

    "linear_team_id": "",
    "_comment_linear_team_id": "(Linear only) Team ID from Linear workspace"
  },

  "ai": {
    "provider": "anthropic",
    "_comment_provider": "AI provider: 'anthropic', 'openai', or 'local'",

    "anthropic_api_key": "${ANTHROPIC_API_KEY}",
    "_comment_anthropic_api_key": "(Anthropic only) Get from https://console.anthropic.com/",

    "openai_api_key": "${OPENAI_API_KEY}",
    "_comment_openai_api_key": "(OpenAI only) Get from https://platform.openai.com/api-keys",

    "model": "claude-3-haiku-20240307",
    "_comment_model": "Model name. For Anthropic: claude-3-haiku-20240307, claude-3-sonnet-20240229. For OpenAI: gpt-4, gpt-3.5-turbo",

    "temperature": 0.7,
    "_comment_temperature": "Sampling temperature (0.0-1.0). Lower = more focused, higher = more creative",

    "max_tokens": 4096,
    "_comment_max_tokens": "Maximum tokens in AI responses",

    "enabled": true,
    "_comment_enabled": "Set false to disable AI features (use rule-based only)"
  },

  "features": {
    "events": true,
    "_comment_events": "Enable event logging for visualization",

    "context": true,
    "_comment_context": "Enable context system (task dependencies, artifacts, decisions)",

    "memory": true,
    "_comment_memory": "Enable memory/learning system (task outcome predictions)",

    "visibility": false,
    "_comment_visibility": "Enable visibility features (experimental)"
  },

  "hybrid_inference": {
    "_comment_section": "Configuration for hybrid dependency inference (pattern + AI)",

    "pattern_confidence_threshold": 0.8,
    "_comment_pattern_confidence_threshold": "Minimum confidence for pattern-based dependencies (0.0-1.0)",

    "ai_confidence_threshold": 0.7,
    "_comment_ai_confidence_threshold": "Minimum confidence for AI-inferred dependencies (0.0-1.0)",

    "combined_confidence_boost": 0.15,
    "_comment_combined_confidence_boost": "Confidence boost when both methods agree (0.0-1.0)",

    "max_ai_pairs_per_batch": 20,
    "_comment_max_ai_pairs_per_batch": "Maximum task pairs to analyze with AI per batch (controls cost)",

    "min_shared_keywords": 2,
    "_comment_min_shared_keywords": "Minimum shared keywords for pattern matching",

    "enable_ai_inference": true,
    "_comment_enable_ai_inference": "Enable AI-based dependency inference (costs API calls)",

    "cache_ttl_hours": 24,
    "_comment_cache_ttl_hours": "Cache dependency analysis for this many hours",

    "require_component_match": true,
    "_comment_require_component_match": "Require component names to match for dependencies",

    "max_dependency_chain_length": 10,
    "_comment_max_dependency_chain_length": "Maximum allowed dependency chain length"
  },

  "task_lease": {
    "_comment_section": "Task lease management prevents agents from holding tasks indefinitely",

    "default_hours": 2.0,
    "_comment_default_hours": "Default lease duration in hours",

    "max_renewals": 10,
    "_comment_max_renewals": "Maximum number of times an agent can renew a lease",

    "warning_hours": 0.5,
    "_comment_warning_hours": "Send warning this many hours before lease expires",

    "grace_period_minutes": 30,
    "_comment_grace_period_minutes": "Grace period after expiry before reclaiming task",

    "renewal_decay_factor": 0.9,
    "_comment_renewal_decay_factor": "Reduce lease time by this factor on each renewal",

    "min_lease_hours": 1.0,
    "_comment_min_lease_hours": "Minimum lease duration",

    "max_lease_hours": 24.0,
    "_comment_max_lease_hours": "Maximum lease duration",

    "stuck_threshold_renewals": 5,
    "_comment_stuck_threshold_renewals": "Number of renewals before task is considered stuck",

    "enable_adaptive": true,
    "_comment_enable_adaptive": "Adjust lease duration based on task priority/complexity",

    "priority_multipliers": {
      "critical": 0.5,
      "high": 0.75,
      "medium": 1.0,
      "low": 1.5,
      "_comment": "Multiply lease time by priority (lower = shorter lease for urgent tasks)"
    },

    "complexity_multipliers": {
      "simple": 0.5,
      "complex": 1.5,
      "research": 2.0,
      "epic": 3.0,
      "_comment": "Multiply lease time by complexity (complex tasks need more time)"
    }
  },

  "board_health": {
    "stale_task_days": 7,
    "_comment_stale_task_days": "Days before a task is considered stale",

    "max_tasks_per_agent": 3,
    "_comment_max_tasks_per_agent": "Maximum tasks an agent can have assigned (Marcus enforces 1 currently)"
  },

  "transport": {
    "type": "http",
    "_comment_type": "MCP transport: 'http' or 'stdio'",

    "http": {
      "host": "0.0.0.0",
      "_comment_host": "HTTP server host (0.0.0.0 = all interfaces, 127.0.0.1 = localhost only)",

      "port": 4298,
      "_comment_port": "HTTP server port",

      "path": "/mcp",
      "_comment_path": "HTTP endpoint path",

      "log_level": "info",
      "_comment_log_level": "Logging level: debug, info, warning, error"
    }
  },

  "multi_endpoint": {
    "_comment_section": "Multiple MCP endpoints for different client types",

    "human": {
      "enabled": true,
      "port": 4298,
      "host": "127.0.0.1",
      "path": "/mcp",
      "_comment": "Endpoint for human users (full access)"
    },

    "agent": {
      "enabled": true,
      "port": 4299,
      "host": "127.0.0.1",
      "path": "/mcp",
      "_comment": "Endpoint for AI agents (restricted to agent tools)"
    },

    "analytics": {
      "enabled": true,
      "port": 4300,
      "host": "127.0.0.1",
      "path": "/mcp",
      "_comment": "Endpoint for analytics/observability (read-only)"
    }
  },

  "log_level": "INFO",
  "_comment_log_level": "Global logging level: DEBUG, INFO, WARNING, ERROR",

  "data_dir": "~/.marcus/data",
  "_comment_data_dir": "Directory for Marcus data (will be created if doesn't exist)",

  "cache_dir": "~/.marcus/cache",
  "_comment_cache_dir": "Directory for cache files (will be created if doesn't exist)"
}
```

#### Step 4.2: Create quick start guide

Create `docs/CONFIGURATION.md`:

```markdown
# Marcus Configuration Guide

## Quick Start

1. **Copy the example config:**
   ```bash
   cp config_marcus.example.json config_marcus.json
   ```

2. **Set your API key:**

   Either edit the file:
   ```json
   {
     "ai": {
       "anthropic_api_key": "sk-ant-api03-your-key-here"
     }
   }
   ```

   Or use environment variable:
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-api03-your-key-here"
   ```

3. **Configure Kanban:**

   For Planka (default):
   ```json
   {
     "kanban": {
       "provider": "planka",
       "planka_base_url": "http://localhost:3333",
       "planka_email": "demo@demo.demo",
       "planka_password": "demo"
     }
   }
   ```

   For GitHub:
   ```json
   {
     "kanban": {
       "provider": "github",
       "github_token": "${GITHUB_TOKEN}",
       "github_owner": "yourusername",
       "github_repo": "yourrepo"
     }
   }
   ```

4. **Start Marcus:**
   ```bash
   docker-compose up -d
   ```

## Configuration Options

See `config_marcus.example.json` for complete documentation of all options.

### Essential Settings

| Setting | Required | Default | Description |
|---------|----------|---------|-------------|
| `ai.anthropic_api_key` | Yes (if using Anthropic) | - | API key from https://console.anthropic.com/ |
| `kanban.provider` | Yes | "planka" | Kanban provider: planka, github, linear |
| `kanban.planka_base_url` | Yes (if Planka) | - | URL to Planka server |
| `kanban.planka_email` | Yes (if Planka) | - | Planka user email |

### Environment Variables

You can override any config value with environment variables:

```bash
export ANTHROPIC_API_KEY="sk-..."
export PLANKA_BASE_URL="http://localhost:3333"
export PLANKA_AGENT_EMAIL="agent@example.com"
export PLANKA_AGENT_PASSWORD="password"
export MARCUS_LOG_LEVEL="DEBUG"
```

In config file, reference with `${VAR_NAME}`:
```json
{
  "ai": {
    "anthropic_api_key": "${ANTHROPIC_API_KEY}"
  }
}
```

### Docker Configuration

When using Docker, you can:

1. **Mount config file:**
   ```yaml
   volumes:
     - ./config_marcus.json:/app/config_marcus.json
   ```

2. **Use environment variables:**
   ```yaml
   environment:
     - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
     - PLANKA_BASE_URL=http://planka:1337
   ```

3. **Specify config file location:**
   ```yaml
   environment:
     - MARCUS_CONFIG=/app/configs/production.json
   ```

## Troubleshooting

### "Configuration validation failed: anthropic_api_key is not set"

**Solution:** Set your API key in `config_marcus.json` or environment:
```bash
export ANTHROPIC_API_KEY="sk-ant-api03-..."
```

### "Cannot connect to Planka server"

**Solution:** Check that:
1. Planka is running: `curl http://localhost:3333/api/health`
2. URL in config matches: `"planka_base_url": "http://localhost:3333"`
3. Credentials are correct

### "Port already in use"

**Solution:** Change ports in config:
```json
{
  "transport": {
    "http": {
      "port": 4299
    }
  }
}
```

## Advanced Configuration

### Multiple Environments

Create separate config files:
- `config_marcus.development.json`
- `config_marcus.production.json`

Switch between them:
```bash
export MARCUS_CONFIG=config_marcus.production.json
```

### Feature Flags

Disable features you don't need:
```json
{
  "features": {
    "memory": false,
    "visibility": false
  }
}
```

### Custom AI Models

Use different models:
```json
{
  "ai": {
    "provider": "anthropic",
    "model": "claude-3-sonnet-20240229",
    "temperature": 0.5
  }
}
```
```

#### Step 4.3: Update README.md with configuration section

Add to `README.md`:

```markdown
## Configuration

Marcus uses a single configuration file for all settings.

### Quick Setup

1. Copy the example config:
   ```bash
   cp config_marcus.example.json config_marcus.json
   ```

2. Set your API key:
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-api03-your-key-here"
   ```

3. Configure Kanban (for Planka):
   ```json
   {
     "kanban": {
       "provider": "planka",
       "planka_base_url": "http://localhost:3333",
       "planka_email": "demo@demo.demo",
       "planka_password": "demo"
     }
   }
   ```

4. Start Marcus:
   ```bash
   docker-compose up -d
   ```

See [Configuration Guide](docs/CONFIGURATION.md) for complete documentation.
```

**Success Criteria**:
- ✅ Example config covers all options
- ✅ Comments explain each setting
- ✅ Quick start guide is clear
- ✅ User can get started in < 5 minutes

---

### Friday: Testing, Documentation & Backward Compatibility

**What**: Final testing, ensure backward compatibility, close Issue #68.

**Why**:
- Ensure existing deployments don't break
- Catch any edge cases
- Document the change
- Ready for merge

**How**:

#### Step 5.1: Test backward compatibility

Create `tests/integration/config/test_backward_compatibility.py`:

```python
"""
Integration tests for backward compatibility.

These tests ensure that old configuration methods still work.
"""

import json
import os
from pathlib import Path

import pytest


@pytest.mark.integration
class TestBackwardCompatibility:
    """Test that old config methods still work"""

    def test_old_planka_config_key_works(self, tmp_path, monkeypatch):
        """Test that old 'planka' top-level key still works."""
        # Change to tmp directory
        monkeypatch.chdir(tmp_path)

        # Create old-style config
        config_file = tmp_path / "config_marcus.json"
        config_data = {
            "planka": {
                "base_url": "http://old-style:3333",
                "email": "old@test.com",
                "password": "oldpass"
            },
            "ai": {
                "provider": "anthropic",
                "anthropic_api_key": "test-key"
            }
        }

        with open(config_file, "w") as f:
            json.dump(config_data, f)

        # Load config
        from src.config.marcus_config import MarcusConfig
        config = MarcusConfig.from_file(str(config_file))

        # Should map to new kanban.planka_* fields
        assert config.kanban.planka_base_url == "http://old-style:3333"
        assert config.kanban.planka_email == "old@test.com"
        assert config.kanban.planka_password == "oldpass"

    def test_env_vars_still_work(self, monkeypatch):
        """Test that environment variables still override config."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-override-key")

        from src.config.marcus_config import MarcusConfig
        config = MarcusConfig.from_env()

        assert config.ai.anthropic_api_key == "env-override-key"

    def test_missing_optional_fields_use_defaults(self, tmp_path, monkeypatch):
        """Test that missing optional config fields use defaults."""
        monkeypatch.chdir(tmp_path)

        # Minimal config (only required fields)
        config_file = tmp_path / "config_marcus.json"
        config_data = {
            "ai": {
                "provider": "anthropic",
                "anthropic_api_key": "test-key"
            },
            "kanban": {
                "provider": "planka",
                "planka_base_url": "http://localhost:3333",
                "planka_email": "test@test.com",
                "planka_password": "testpass"
            }
            # Missing: features, hybrid_inference, task_lease, etc.
        }

        with open(config_file, "w") as f:
            json.dump(config_data, f)

        # Load config
        from src.config.marcus_config import MarcusConfig
        config = MarcusConfig.from_file(str(config_file))

        # Should use defaults
        assert config.features.events is True
        assert config.task_lease.default_hours == 2.0
        assert config.hybrid_inference.enable_ai_inference is True


@pytest.mark.integration
def test_server_starts_with_new_config(tmp_path, monkeypatch):
    """Test that Marcus server starts with new config system."""
    monkeypatch.chdir(tmp_path)

    # Create valid config
    config_file = tmp_path / "config_marcus.json"
    config_data = {
        "ai": {
            "provider": "anthropic",
            "anthropic_api_key": "sk-test-key-for-server-start",
            "enabled": True
        },
        "kanban": {
            "provider": "planka",
            "planka_base_url": "http://localhost:3333",
            "planka_email": "test@test.com",
            "planka_password": "testpass"
        }
    }

    with open(config_file, "w") as f:
        json.dump(config_data, f)

    # Import server (will load config)
    from src.config.marcus_config import get_config, reload_config

    # Force reload to pick up our test config
    reload_config()

    config = get_config()

    # Should have loaded our test config
    assert config.ai.anthropic_api_key == "sk-test-key-for-server-start"
    assert config.kanban.planka_base_url == "http://localhost:3333"
```

Run tests:
```bash
pytest tests/integration/config/test_backward_compatibility.py -v
```

#### Step 5.2: Full regression testing

Run all existing tests to ensure nothing broke:

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run all integration tests
pytest tests/integration/ -v

# Check test coverage
pytest --cov=src/config --cov-report=html
```

#### Step 5.3: Update CHANGELOG

Add to `CHANGELOG.md`:

```markdown
## [Unreleased]

### Added
- **Configuration Management (#68)**: Centralized configuration system
  - Single `config_marcus.json` file for all settings
  - Type-safe dataclass-based configuration
  - Environment variable override support (`${ENV_VAR}` syntax)
  - Validation on startup with clear error messages
  - Backward compatible with existing deployments
  - See `config_marcus.example.json` and `docs/CONFIGURATION.md`

### Changed
- All hard-coded configuration values moved to central config
- Configuration now validated at startup (catches errors early)

### Migration Guide
1. Copy `config_marcus.example.json` to `config_marcus.json`
2. Fill in your API keys and Kanban credentials
3. Old environment variables still work (no breaking changes)
4. See `docs/CONFIGURATION.md` for complete guide
```

#### Step 5.4: Create pull request

Create a feature branch:
```bash
git checkout -b feature/centralized-config-68
git add .
git commit -m "[#68] Centralize configuration management

- Add src/config/marcus_config.py with dataclass structure
- Add validation with clear error messages
- Support file and environment variable loading
- Create config_marcus.example.json template
- Migrate all existing code to use get_config()
- Add comprehensive tests
- Document in docs/CONFIGURATION.md
- Maintain backward compatibility

Closes #68"
git push origin feature/centralized-config-68
```

Create PR on GitHub with description:

```markdown
## Summary
Implements centralized configuration management as described in Issue #68.

## Changes
- ✅ Type-safe configuration with dataclasses
- ✅ Single source of truth (`config_marcus.json`)
- ✅ Validation on startup
- ✅ Environment variable override support
- ✅ Backward compatible
- ✅ Comprehensive tests (unit + integration)
- ✅ User documentation

## Testing
```bash
# All tests pass
pytest tests/unit/config/ -v
pytest tests/integration/config/ -v

# Coverage: 95%
pytest --cov=src/config --cov-report=term

# Manual testing
./scripts/test_config_migration.sh
```

## Migration Impact
- No breaking changes
- Old environment variables still work
- Old `planka` config key still works
- Existing deployments continue to work

## Documentation
- `config_marcus.example.json` - User-facing template
- `docs/CONFIGURATION.md` - Complete configuration guide
- README.md updated with quick start

## Closes
Closes #68
```

**Success Criteria**:
- ✅ All tests pass (unit + integration)
- ✅ Backward compatibility verified
- ✅ Documentation complete
- ✅ PR ready for review
- ✅ Issue #68 can be closed

---

## Week 1 Summary

**Deliverables**:
1. ✅ `src/config/marcus_config.py` - Type-safe config system
2. ✅ Validation with clear error messages
3. ✅ Environment variable override support
4. ✅ `config_marcus.example.json` - User template
5. ✅ `docs/CONFIGURATION.md` - Configuration guide
6. ✅ All existing code migrated
7. ✅ Comprehensive tests
8. ✅ Backward compatibility maintained
9. ✅ Issue #68 closed

**What This Enables**:
- Easy deployment (one config file)
- Clear documentation (users know what to configure)
- Foundation for all Week 2-6 work
- Packaging is solved (users copy example, fill in values)

**Next Week**: Week 2 - Workspace Isolation Phase 1 (Foundation)

---
