"""
Custom exceptions for the headless research system.
Provides clear error types for different failure modes.
"""

from typing import Optional, Dict, Any


class HeadlessResearchError(Exception):
    """Base exception for all headless research errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details or {}


class ClaudeError(HeadlessResearchError):
    """Base exception for Claude-related errors"""
    pass


class ClaudeNotFoundError(ClaudeError):
    """Claude CLI is not installed or not accessible"""
    pass


class ClaudeExecutionError(ClaudeError):
    """Claude command execution failed"""
    
    def __init__(self, message: str, exit_code: int, stderr: str = ""):
        super().__init__(message, {
            'exit_code': exit_code,
            'stderr': stderr
        })
        self.exit_code = exit_code
        self.stderr = stderr


class ClaudeTimeoutError(ClaudeError):
    """Claude execution timed out"""
    
    def __init__(self, message: str, timeout_seconds: int):
        super().__init__(message, {'timeout_seconds': timeout_seconds})
        self.timeout_seconds = timeout_seconds


class AgentError(HeadlessResearchError):
    """Base exception for agent-related errors"""
    
    def __init__(self, agent_name: str, message: str, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details['agent_name'] = agent_name
        super().__init__(message, details)
        self.agent_name = agent_name


class AgentNotFoundError(AgentError):
    """Agent definition not found"""
    pass


class AgentExecutionError(AgentError):
    """Agent execution failed"""
    pass


class TokenLimitError(HeadlessResearchError):
    """Token budget exceeded"""
    
    def __init__(self, used: int, budget: int, message: Optional[str] = None):
        message = message or f"Token limit exceeded: {used}/{budget}"
        super().__init__(message, {
            'tokens_used': used,
            'token_budget': budget
        })
        self.tokens_used = used
        self.token_budget = budget


class RateLimitError(HeadlessResearchError):
    """Rate limit exceeded"""
    
    def __init__(self, retry_after: Optional[float] = None):
        message = "Rate limit exceeded"
        if retry_after:
            message += f" (retry after {retry_after}s)"
        super().__init__(message, {'retry_after': retry_after})
        self.retry_after = retry_after


class WorkspaceError(HeadlessResearchError):
    """Workspace-related errors"""
    pass


class CacheError(HeadlessResearchError):
    """Cache-related errors"""
    pass


class ExtractionError(HeadlessResearchError):
    """Data extraction failed"""
    
    def __init__(self, message: str, raw_output: str):
        super().__init__(message, {'raw_output_preview': raw_output[:500]})
        self.raw_output = raw_output


class OrchestrationError(HeadlessResearchError):
    """Orchestration-level errors"""
    pass


class ConfigurationError(HeadlessResearchError):
    """Configuration-related errors"""
    pass


class CircuitBreakerError(HeadlessResearchError):
    """Circuit breaker is open"""
    
    def __init__(self, service: str, message: Optional[str] = None):
        message = message or f"Circuit breaker open for service: {service}"
        super().__init__(message, {'service': service})
        self.service = service
