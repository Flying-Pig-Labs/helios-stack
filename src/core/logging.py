"""
Structured logging for headless research system.
Provides JSON logging, performance tracking, and Claude output capture.
"""

import logging
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import traceback
from contextlib import contextmanager
import time

from .config import get_config


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logs"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add extra fields
        if hasattr(record, 'agent_name'):
            log_data['agent_name'] = record.agent_name
        if hasattr(record, 'tokens_used'):
            log_data['tokens_used'] = record.tokens_used
        if hasattr(record, 'execution_time'):
            log_data['execution_time'] = record.execution_time
        if hasattr(record, 'error_type'):
            log_data['error_type'] = record.error_type
            
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        return json.dumps(log_data)


class AgentLogger(logging.LoggerAdapter):
    """Logger adapter for agent-specific context"""
    
    def __init__(self, logger: logging.Logger, agent_name: str):
        super().__init__(logger, {'agent_name': agent_name})
    
    def process(self, msg, kwargs):
        # Add agent name to all log records
        extra = kwargs.get('extra', {})
        extra['agent_name'] = self.extra['agent_name']
        kwargs['extra'] = extra
        return msg, kwargs


class PerformanceLogger:
    """Track and log performance metrics"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.metrics: Dict[str, Any] = {}
    
    @contextmanager
    def track_execution(self, operation: str, **tags):
        """Context manager to track execution time"""
        start_time = time.time()
        
        try:
            yield
        finally:
            execution_time = time.time() - start_time
            self.logger.info(
                f"{operation} completed",
                extra={
                    'operation': operation,
                    'execution_time': execution_time,
                    **tags
                }
            )
    
    def log_token_usage(self, agent_name: str, tokens: int, operation: str):
        """Log token consumption"""
        self.logger.info(
            "Token usage recorded",
            extra={
                'agent_name': agent_name,
                'tokens_used': tokens,
                'operation': operation
            }
        )
    
    def log_cache_hit(self, cache_key: str, size_bytes: int):
        """Log cache hit"""
        self.logger.debug(
            "Cache hit",
            extra={
                'cache_key': cache_key,
                'size_bytes': size_bytes
            }
        )
    
    def log_rate_limit(self, agent_name: str, wait_time: float):
        """Log rate limiting event"""
        self.logger.warning(
            "Rate limit encountered",
            extra={
                'agent_name': agent_name,
                'wait_time': wait_time
            }
        )


class ClaudeOutputLogger:
    """Capture and log Claude command outputs"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.config = get_config()
    
    def log_command(self, cmd: list, workspace: Optional[Path] = None):
        """Log Claude command execution"""
        if self.config.logging.log_claude_output:
            self.logger.debug(
                "Executing Claude command",
                extra={
                    'command': ' '.join(cmd),
                    'workspace': str(workspace) if workspace else None
                }
            )
    
    def log_output(self, agent_name: str, output: str, error: str = None):
        """Log Claude output"""
        if self.config.logging.log_claude_output:
            log_data = {
                'agent_name': agent_name,
                'output_length': len(output),
                'has_error': bool(error)
            }
            
            if self.config.debug_mode:
                log_data['output_preview'] = output[:500]
                if error:
                    log_data['error'] = error
            
            self.logger.debug("Claude output captured", extra=log_data)


def setup_logging() -> logging.Logger:
    """Set up the logging system"""
    config = get_config()
    
    # Create root logger
    root_logger = logging.getLogger("headless_research")
    root_logger.setLevel(getattr(logging, config.logging.level))
    
    # Remove existing handlers
    root_logger.handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    if config.logging.format == "json":
        console_handler.setFormatter(StructuredFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        )
    root_logger.addHandler(console_handler)
    
    # File handler
    if config.logging.log_to_file:
        log_file = config.logging.log_dir / f"research_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(file_handler)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance"""
    return logging.getLogger(f"headless_research.{name}")


def get_agent_logger(agent_name: str) -> AgentLogger:
    """Get an agent-specific logger"""
    base_logger = get_logger(f"agents.{agent_name}")
    return AgentLogger(base_logger, agent_name)


# Initialize logging on module import
setup_logging()
