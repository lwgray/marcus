"""Centralized configuration for Marcus.

This module provides type-safe configuration management with:
- Dataclass-based structure for type safety
- Environment variable override support
- Validation on startup
- Clear defaults

Example
-------
>>> from src.config.marcus_config import get_config
>>> config = get_config()
>>> api_key = config.ai.anthropic_api_key
>>> planka_url = config.kanban.planka_base_url
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class MCPSettings:
    """MCP (Model Context Protocol) related configuration.

    Parameters
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
    """AI provider configuration.

    Parameters
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
    """Kanban provider configuration.

    Parameters
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
    """Feature flags for optional Marcus features.

    Parameters
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
class TransportSettings:
    """MCP transport configuration.

    Parameters
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
    http_host: str = "0.0.0.0"  # nosec B104
    http_port: int = 4298
    http_path: str = "/mcp"
    log_level: str = "info"


@dataclass
class MarcusConfig:
    """Central configuration for Marcus.

    This is the main configuration class that contains all settings.
    Load it once at startup and use throughout the application.

    Parameters
    ----------
    mcp : MCPSettings
        MCP-related settings
    ai : AISettings
        AI provider settings
    kanban : KanbanSettings
        Kanban provider settings
    features : FeaturesSettings
        Feature flags
    transport : TransportSettings
        MCP transport settings
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
    transport: TransportSettings = field(default_factory=TransportSettings)

    # Global settings
    auto_find_board: bool = False
    single_project_mode: bool = True
    log_level: str = "INFO"
    data_dir: str = "~/.marcus/data"
    cache_dir: str = "~/.marcus/cache"

    @classmethod
    def from_file(cls, path: str = "config_marcus.json") -> "MarcusConfig":
        """Load configuration from JSON file.

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

        Examples
        --------
        >>> config = MarcusConfig.from_file("config_marcus.json")
        >>> print(config.ai.provider)
        "anthropic"
        """
        config_path = Path(path).expanduser()

        # If config file doesn't exist, return defaults
        if not config_path.exists():
            import sys

            print(
                f"Warning: Config file not found at {config_path}, using defaults",
                file=sys.stderr,
            )
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
        """Recursively substitute ${ENV_VAR} with environment variable values.

        Examples
        --------
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
    def _from_dict(cls, data: dict[str, Any]) -> "MarcusConfig":
        """Create MarcusConfig from dictionary.

        Handles nested dataclasses by recursively creating them.
        """
        # Create nested configs
        nested_configs: dict[str, Any] = {}

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

        if "transport" in data:
            transport_data = data["transport"]
            if isinstance(transport_data.get("http"), dict):
                # New format with nested http section
                http_config = transport_data["http"]
                port = http_config.get("port", 4298)
                # Convert string to int if needed (from env var substitution)
                if isinstance(port, str):
                    port = int(port)
                nested_configs["transport"] = TransportSettings(
                    type=transport_data.get("type", "http"),
                    http_host=http_config.get("host", "0.0.0.0"),  # nosec B104
                    http_port=port,
                    http_path=http_config.get("path", "/mcp"),
                    log_level=http_config.get("log_level", "info"),
                )
            else:
                # Old flat format
                nested_configs["transport"] = TransportSettings(**transport_data)

        # Extract top-level settings
        top_level = {
            "auto_find_board": data.get("auto_find_board", False),
            "single_project_mode": data.get("single_project_mode", True),
            "log_level": data.get("log_level", "INFO"),
            "data_dir": data.get("data_dir", "~/.marcus/data"),
            "cache_dir": data.get("cache_dir", "~/.marcus/cache"),
        }

        # Combine nested and top-level
        return cls(**nested_configs, **top_level)

    def validate(self) -> None:
        """Validate configuration settings.

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

        Examples
        --------
        >>> config = MarcusConfig.from_file("config.json")
        >>> config.validate()  # Raises ValueError if invalid
        """
        errors: list[str] = []

        # Validate AI settings
        if self.ai.enabled:
            if self.ai.provider == "anthropic":
                if not self.ai.anthropic_api_key:
                    errors.append(
                        "AI provider is 'anthropic' but anthropic_api_key is not set. "
                        "Set it in config_marcus.json or environment variable "
                        "ANTHROPIC_API_KEY"
                    )
            elif self.ai.provider == "openai":
                if not self.ai.openai_api_key:
                    errors.append(
                        "AI provider is 'openai' but openai_api_key is not set. "
                        "Set it in config_marcus.json or environment variable "
                        "OPENAI_API_KEY"
                    )

            # Validate temperature
            if not 0.0 <= self.ai.temperature <= 1.0:
                errors.append(
                    f"AI temperature must be between 0.0 and 1.0, "
                    f"got {self.ai.temperature}"
                )

        # Validate Kanban settings
        if self.kanban.provider == "planka":
            if not self.kanban.planka_base_url:
                errors.append(
                    "Kanban provider is 'planka' but planka_base_url is not set"
                )
            if not self.kanban.planka_email:
                errors.append("Kanban provider is 'planka' but planka_email is not set")
            if not self.kanban.planka_password:
                errors.append(
                    "Kanban provider is 'planka' but planka_password is not set"
                )
        elif self.kanban.provider == "github":
            if not self.kanban.github_token:
                errors.append("Kanban provider is 'github' but github_token is not set")
            if not self.kanban.github_owner or not self.kanban.github_repo:
                errors.append(
                    "Kanban provider is 'github' but github_owner or "
                    "github_repo is not set"
                )
        elif self.kanban.provider == "linear":
            if not self.kanban.linear_api_key:
                errors.append(
                    "Kanban provider is 'linear' but linear_api_key is not set"
                )

        # Validate transport settings
        if self.transport.http_port < 1 or self.transport.http_port > 65535:
            errors.append(
                f"Transport HTTP port must be between 1-65535, "
                f"got {self.transport.http_port}"
            )

        # Validate directories can be created
        for dir_name, dir_path in [
            ("data_dir", self.data_dir),
            ("cache_dir", self.cache_dir),
        ]:
            try:
                path = Path(dir_path).expanduser()
                path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"Cannot create {dir_name} at {dir_path}: {e}")

        # If there are errors, raise with clear message
        if errors:
            error_message = "Configuration validation failed:\n\n"
            for i, error in enumerate(errors, 1):
                error_message += f"{i}. {error}\n"
            error_message += "\nPlease fix these issues in config_marcus.json"
            raise ValueError(error_message)


# Global config instance
_config: Optional[MarcusConfig] = None


def get_config() -> MarcusConfig:
    """Get or create global config instance.

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

    Examples
    --------
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
    """Force reload configuration from file.

    Useful for:
    - Testing (reset config between tests)
    - Hot-reloading config changes

    Returns
    -------
    MarcusConfig
        The reloaded configuration

    Examples
    --------
    >>> config = reload_config()  # Force fresh load from disk
    """
    global _config
    config_path = os.getenv("MARCUS_CONFIG", "config_marcus.json")
    _config = MarcusConfig.from_file(config_path)
    _config.validate()
    return _config
