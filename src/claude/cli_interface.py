# src/claude/cli_interface.py
"""
Claude CLI wrapper for headless execution.
Handles subprocess management, output capture, and error handling.
"""

import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
import shlex
import os

from ..core.config import get_config
from ..core.logging import get_logger, ClaudeOutputLogger
from ..core.exceptions import (
    ClaudeExecutionError,
    ClaudeTimeoutError,
    ClaudeNotFoundError
)

logger = get_logger(__name__)


@dataclass
class ClaudeResult:
    """Result from Claude CLI execution"""
    success: bool
    output: str
    error: str
    exit_code: int
    execution_time: float
    command: str
    workspace: Optional[Path] = None
    
    @property
    def combined_output(self) -> str:
        """Get combined stdout and stderr"""
        return self.output + ("\n" + self.error if self.error else "")


class ClaudeInterface:
    """Wrapper for Claude CLI interactions"""
    
    def __init__(self):
        self.config = get_config()
        self.output_logger = ClaudeOutputLogger(logger)
        self._verify_claude_available()
    
    def _verify_claude_available(self):
        """Verify Claude CLI is available"""
        if self.config.dry_run:
            logger.info("Dry run mode - skipping Claude CLI verification")
            return
            
        try:
            result = subprocess.run(
                [self.config.claude.cli_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                raise ClaudeNotFoundError(
                    f"Claude CLI failed version check: {result.stderr}"
                )
            logger.info(f"Claude CLI verified: {result.stdout.strip()}")
        except FileNotFoundError:
            raise ClaudeNotFoundError(
                f"Claude CLI not found at: {self.config.claude.cli_path}"
            )
        except subprocess.TimeoutExpired:
            raise ClaudeNotFoundError("Claude CLI version check timed out")
    
    async def execute(
        self,
        prompt: str,
        workspace: Optional[Path] = None,
        timeout: Optional[int] = None,
        env_vars: Optional[Dict[str, str]] = None
    ) -> ClaudeResult:
        """Execute a Claude command asynchronously"""
        
        # Build command
        cmd = self._build_command(prompt)
        self.output_logger.log_command(cmd, workspace)
        
        # Set up environment
        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)
        
        # Use specified timeout or default
        timeout = timeout or self.config.claude.default_timeout
        
        # Execute
        start_time = asyncio.get_event_loop().time()
        
        try:
            if self.config.dry_run:
                # Simulate execution in dry run mode
                await asyncio.sleep(0.1)
                return ClaudeResult(
                    success=True,
                    output=f"[DRY RUN] Would execute: {' '.join(cmd)}",
                    error="",
                    exit_code=0,
                    execution_time=0.1,
                    command=' '.join(cmd),
                    workspace=workspace
                )
            
            # Create subprocess
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(workspace) if workspace else None,
                env=env
            )
            
            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                # Kill the process
                process.kill()
                await process.wait()
                raise ClaudeTimeoutError(
                    f"Claude execution timed out after {timeout}s",
                    timeout_seconds=timeout
                )
            
            # Decode output
            output = stdout.decode('utf-8', errors='replace')
            error = stderr.decode('utf-8', errors='replace')
            
            execution_time = asyncio.get_event_loop().time() - start_time
            
            result = ClaudeResult(
                success=process.returncode == 0,
                output=output,
                error=error,
                exit_code=process.returncode,
                execution_time=execution_time,
                command=' '.join(cmd),
                workspace=workspace
            )
            
            # Log output
            self.output_logger.log_output(
                agent_name="claude",
                output=output,
                error=error if process.returncode != 0 else None
            )
            
            return result
            
        except Exception as e:
            # Log and re-raise
            logger.error(
                f"Claude execution failed: {e}",
                exc_info=True,
                extra={'command': ' '.join(cmd)}
            )
            raise
    
    def execute_sync(
        self,
        prompt: str,
        workspace: Optional[Path] = None,
        timeout: Optional[int] = None,
        env_vars: Optional[Dict[str, str]] = None
    ) -> ClaudeResult:
        """Synchronous wrapper for execute"""
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(
            self.execute(prompt, workspace, timeout, env_vars)
        )
    
    def _build_command(self, prompt: str) -> list:
        """Build the Claude command"""
        cmd = [self.config.claude.cli_path, "-p", prompt]
        
        # Add any additional flags from config
        # Note: Based on our testing, most flags don't work as expected
        # so we keep it simple
        
        return cmd
    
    async def execute_batch(
        self,
        prompts: list[Tuple[str, Optional[Path]]],
        max_concurrent: Optional[int] = None
    ) -> list[ClaudeResult]:
        """Execute multiple prompts with concurrency control"""
        
        max_concurrent = max_concurrent or self.config.claude.max_concurrent
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def run_with_semaphore(prompt: str, workspace: Optional[Path]):
            async with semaphore:
                return await self.execute(prompt, workspace)
        
        tasks = [
            run_with_semaphore(prompt, workspace)
            for prompt, workspace in prompts
        ]
        
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    def test_connection(self) -> bool:
        """Test Claude CLI is responsive"""
        try:
            result = self.execute_sync(
                "Say 'Connection test successful'",
                timeout=10
            )
            return result.success and "successful" in result.output.lower()
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False


class ClaudeSubAgentInterface(ClaudeInterface):
    """Extended interface for sub-agent execution"""
    
    async def execute_with_agent(
        self,
        agent_name: str,
        query: str,
        workspace: Optional[Path] = None,
        timeout: Optional[int] = None
    ) -> ClaudeResult:
        """Execute a query using a specific sub-agent"""
        
        # Format prompt for sub-agent invocation
        prompt = f"Use {agent_name} to {query}"
        
        # Log agent invocation
        logger.info(
            f"Invoking sub-agent",
            extra={
                'agent_name': agent_name,
                'query_length': len(query)
            }
        )
        
        # Execute
        result = await self.execute(prompt, workspace, timeout)
        
        # Add agent context to result
        if hasattr(result, '__dict__'):
            result.__dict__['agent_name'] = agent_name
        
        return result
    
    def verify_agent_exists(self, agent_name: str) -> bool:
        """Check if an agent definition exists"""
        agent_file = self.config.agent_dir / f"{agent_name}.md"
        exists = agent_file.exists()
        
        if not exists:
            logger.warning(
                f"Agent not found",
                extra={'agent_name': agent_name, 'path': str(agent_file)}
            )
        
        return exists
