"""
Configuration management for headless research system.
Handles environment variables, settings, and runtime configuration.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
import json
import yaml
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class ClaudeConfig:
    """Claude-specific configuration"""
    cli_path: str = field(default_factory=lambda: os.getenv("CLAUDE_CLI_PATH", "claude"))
    max_concurrent: int = field(default_factory=lambda: int(os.getenv("CLAUDE_MAX_CONCURRENT", "3")))
    default_timeout: int = field(default_factory=lambda: int(os.getenv("CLAUDE_TIMEOUT", "300")))
    retry_attempts: int = field(default_factory=lambda: int(os.getenv("CLAUDE_RETRY_ATTEMPTS", "3")))
    rate_limit_delay: float = field(default_factory=lambda: float(os.getenv("CLAUDE_RATE_LIMIT_DELAY", "1.0")))
    

@dataclass
class TokenConfig:
    """Token management configuration"""
    daily_budget: int = field(default_factory=lambda: int(os.getenv("TOKEN_DAILY_BUDGET", "100000")))
    warning_threshold: float = field(default_factory=lambda: float(os.getenv("TOKEN_WARNING_THRESHOLD", "0.8")))
    tier1_estimate: int = field(default_factory=lambda: int(os.getenv("TOKEN_TIER1_ESTIMATE", "3000")))
    tier2_estimate: int = field(default_factory=lambda: int(os.getenv("TOKEN_TIER2_ESTIMATE", "5000")))
    tier3_estimate: int = field(default_factory=lambda: int(os.getenv("TOKEN_TIER3_ESTIMATE", "8000")))
    tier4_estimate: int = field(default_factory=lambda: int(os.getenv("TOKEN_TIER4_ESTIMATE", "10000")))


@dataclass
class WorkspaceConfig:
    """Workspace and git worktree configuration"""
    base_dir: Path = field(default_factory=lambda: Path(os.getenv("WORKSPACE_BASE_DIR", "/tmp/research_workspaces")))
    use_worktrees: bool = field(default_factory=lambda: os.getenv("USE_GIT_WORKTREES", "true").lower() == "true")
    cleanup_on_exit: bool = field(default_factory=lambda: os.getenv("CLEANUP_WORKSPACES", "true").lower() == "true")
    worktree_prefix: str = field(default_factory=lambda: os.getenv("WORKTREE_PREFIX", "research_"))


@dataclass
class CacheConfig:
    """Caching configuration"""
    enabled: bool = field(default_factory=lambda: os.getenv("CACHE_ENABLED", "true").lower() == "true")
    ttl_seconds: int = field(default_factory=lambda: int(os.getenv("CACHE_TTL_SECONDS", "3600")))
    max_size_mb: int = field(default_factory=lambda: int(os.getenv("CACHE_MAX_SIZE_MB", "500")))
    cache_dir: Path = field(default_factory=lambda: Path(os.getenv("CACHE_DIR", "~/.cache/headless_research")).expanduser())


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    format: str = field(default_factory=lambda: os.getenv("LOG_FORMAT", "json"))
    log_dir: Path = field(default_factory=lambda: Path(os.getenv("LOG_DIR", "./logs")))
    log_to_file: bool = field(default_factory=lambda: os.getenv("LOG_TO_FILE", "true").lower() == "true")
    log_claude_output: bool = field(default_factory=lambda: os.getenv("LOG_CLAUDE_OUTPUT", "false").lower() == "true")


@dataclass
class ResearchConfig:
    """Overall research system configuration"""
    claude: ClaudeConfig = field(default_factory=ClaudeConfig)
    tokens: TokenConfig = field(default_factory=TokenConfig)
    workspace: WorkspaceConfig = field(default_factory=WorkspaceConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    # Additional settings
    dry_run: bool = field(default_factory=lambda: os.getenv("DRY_RUN", "false").lower() == "true")
    debug_mode: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")
    agent_dir: Path = field(default_factory=lambda: Path(os.getenv("AGENT_DIR", "~/.claude/agents")).expanduser())
    
    @classmethod
    def from_file(cls, config_path: Path) -> "ResearchConfig":
        """Load configuration from YAML or JSON file"""
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            if config_path.suffix in ['.yaml', '.yml']:
                data = yaml.safe_load(f)
            else:
                data = json.load(f)
        
        # Override with environment variables
        return cls._merge_with_env(data)
    
    @classmethod
    def _merge_with_env(cls, data: Dict[str, Any]) -> "ResearchConfig":
        """Merge file config with environment variables (env takes precedence)"""
        # This is simplified - in practice, implement recursive merging
        return cls()
    
    def validate(self) -> None:
        """Validate configuration settings"""
        # Check Claude CLI exists
        if not self.dry_run:
            import shutil
            if not shutil.which(self.claude.cli_path):
                raise ValueError(f"Claude CLI not found at: {self.claude.cli_path}")
        
        # Ensure directories exist
        self.workspace.base_dir.mkdir(parents=True, exist_ok=True)
        self.cache.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logging.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Validate numeric ranges
        if not 0 < self.claude.max_concurrent <= 10:
            raise ValueError(f"Invalid max_concurrent: {self.claude.max_concurrent}")
        
        if not 0 < self.tokens.warning_threshold <= 1:
            raise ValueError(f"Invalid warning_threshold: {self.tokens.warning_threshold}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        def _convert(obj):
            if isinstance(obj, Path):
                return str(obj)
            elif hasattr(obj, '__dict__'):
                return {k: _convert(v) for k, v in obj.__dict__.items()}
            else:
                return obj
        
        return _convert(self)


# Global configuration instance
_config: Optional[ResearchConfig] = None


def get_config() -> ResearchConfig:
    """Get the global configuration instance"""
    global _config
    if _config is None:
        _config = ResearchConfig()
        _config.validate()
    return _config


def set_config(config: ResearchConfig) -> None:
    """Set the global configuration instance"""
    global _config
    config.validate()
    _config = config


def reset_config() -> None:
    """Reset configuration to defaults"""
    global _config
    _config = None
