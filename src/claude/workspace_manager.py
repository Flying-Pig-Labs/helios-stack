"""
Workspace management using git worktrees for agent isolation.
Prevents context bleeding between concurrent Claude instances.
"""

import asyncio
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
import uuid
import tempfile

from ..core.config import get_config
from ..core.logging import get_logger
from ..core.exceptions import WorkspaceError

logger = get_logger(__name__)


class WorkspaceManager:
    """Manages isolated workspaces for Claude agents"""
    
    def __init__(self):
        self.config = get_config()
        self.active_workspaces: Dict[str, Path] = {}
        self._ensure_base_dir()
    
    def _ensure_base_dir(self):
        """Ensure base workspace directory exists"""
        self.config.workspace.base_dir.mkdir(parents=True, exist_ok=True)
    
    async def create_workspace(
        self,
        agent_name: str,
        use_worktree: Optional[bool] = None
    ) -> Path:
        """Create an isolated workspace for an agent"""
        
        workspace_id = f"{self.config.workspace.worktree_prefix}{agent_name}_{uuid.uuid4().hex[:8]}"
        use_worktree = use_worktree if use_worktree is not None else self.config.workspace.use_worktrees
        
        if use_worktree and await self._is_git_repo():
            workspace_path = await self._create_git_worktree(workspace_id)
        else:
            workspace_path = await self._create_temp_workspace(workspace_id)
        
        # Set up agent definitions
        await self._setup_agent_definitions(workspace_path)
        
        self.active_workspaces[workspace_id] = workspace_path
        
        logger.info(
            "Created workspace",
            extra={
                'workspace_id': workspace_id,
                'agent_name': agent_name,
                'path': str(workspace_path),
                'type': 'worktree' if use_worktree else 'temp'
            }
        )
        
        return workspace_path
    
    async def _is_git_repo(self) -> bool:
        """Check if current directory is a git repository"""
        try:
            result = await self._run_command(["git", "rev-parse", "--git-dir"])
            return result.returncode == 0
        except Exception:
            return False
    
    async def _create_git_worktree(self, workspace_id: str) -> Path:
        """Create a git worktree for isolation"""
        
        # Get the main branch name
        result = await self._run_command(["git", "branch", "--show-current"])
        if result.returncode != 0:
            # Fallback to HEAD if detached
            result = await self._run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        
        branch = result.stdout.strip() or "main"
        
        # Create worktree path
        worktree_path = self.config.workspace.base_dir / workspace_id
        
        # Create a new branch for this worktree
        worktree_branch = f"research/{workspace_id}"
        
        # Add worktree
        cmd = [
            "git", "worktree", "add",
            "-b", worktree_branch,
            str(worktree_path),
            branch
        ]
        
        result = await self._run_command(cmd)
        if result.returncode != 0:
            raise WorkspaceError(
                f"Failed to create git worktree: {result.stderr}"
            )
        
        return worktree_path
    
    async def _create_temp_workspace(self, workspace_id: str) -> Path:
        """Create a temporary workspace directory"""
        workspace_path = self.config.workspace.base_dir / workspace_id
        workspace_path.mkdir(parents=True, exist_ok=True)
        
        # Copy essential files if in a git repo
        if await self._is_git_repo():
            # Copy .gitignore, README, etc.
            for pattern in ['.gitignore', 'README.md', 'pyproject.toml']:
                src = Path(pattern)
                if src.exists():
                    dst = workspace_path / pattern
                    if src.is_file():
                        shutil.copy2(src, dst)
                    else:
                        shutil.copytree(src, dst)
        
        return workspace_path
    
    async def _setup_agent_definitions(self, workspace_path: Path):
        """Copy agent definitions to workspace"""
        
        # Create .claude/agents directory
        agents_dir = workspace_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy from user agents directory
        user_agents = self.config.agent_dir
        if user_agents.exists():
            for agent_file in user_agents.glob("*.md"):
                shutil.copy2(agent_file, agents_dir / agent_file.name)
        
        # Copy from project agents if different
        project_agents = Path(".claude/agents")
        if project_agents.exists() and project_agents != user_agents:
            for agent_file in project_agents.glob("*.md"):
                # Project agents override user agents
                shutil.copy2(agent_file, agents_dir / agent_file.name)
    
    async def cleanup_workspace(self, workspace_path: Path):
        """Clean up a workspace"""
        
        workspace_id = workspace_path.name
        
        if not self.config.workspace.cleanup_on_exit:
            logger.info(f"Skipping cleanup for workspace: {workspace_id}")
            return
        
        try:
            # If it's a worktree, remove it properly
            if await self._is_git_worktree(workspace_path):
                await self._remove_git_worktree(workspace_path)
            else:
                # Regular directory removal
                shutil.rmtree(workspace_path, ignore_errors=True)
            
            # Remove from active workspaces
            self.active_workspaces.pop(workspace_id, None)
            
            logger.info(f"Cleaned up workspace: {workspace_id}")
            
        except Exception as e:
            logger.error(f"Failed to cleanup workspace {workspace_id}: {e}")
    
    async def _is_git_worktree(self, path: Path) -> bool:
        """Check if a path is a git worktree"""
        git_file = path / ".git"
        if git_file.exists() and git_file.is_file():
            # .git file indicates a worktree
            return True
        return False
    
    async def _remove_git_worktree(self, worktree_path: Path):
        """Remove a git worktree"""
        
        # First, remove the worktree
        result = await self._run_command([
            "git", "worktree", "remove", "--force", str(worktree_path)
        ])
        
        if result.returncode != 0:
            logger.warning(f"Failed to remove worktree: {result.stderr}")
            # Fallback to manual removal
            shutil.rmtree(worktree_path, ignore_errors=True)
        
        # Clean up the branch
        branch_name = f"research/{worktree_path.name}"
        await self._run_command([
            "git", "branch", "-D", branch_name
        ])
    
    async def cleanup_all(self):
        """Clean up all active workspaces"""
        
        logger.info(f"Cleaning up {len(self.active_workspaces)} workspaces")
        
        cleanup_tasks = [
            self.cleanup_workspace(path)
            for path in self.active_workspaces.values()
        ]
        
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        # Prune worktrees
        if self.config.workspace.use_worktrees:
            await self._run_command(["git", "worktree", "prune"])
    
    async def _run_command(self, cmd: List[str]) -> subprocess.CompletedProcess:
        """Run a command asynchronously"""
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        return subprocess.CompletedProcess(
            cmd,
            process.returncode,
            stdout.decode('utf-8', errors='replace'),
            stderr.decode('utf-8', errors='replace')
        )
    
    @asynccontextmanager
    async def isolated_workspace(self, agent_name: str):
        """Context manager for isolated workspace"""
        workspace = None
        try:
            workspace = await self.create_workspace(agent_name)
            yield workspace
        finally:
            if workspace:
                await self.cleanup_workspace(workspace)
    
    def list_active_workspaces(self) -> List[Dict[str, str]]:
        """List all active workspaces"""
        return [
            {
                'id': workspace_id,
                'path': str(path),
                'exists': path.exists()
            }
            for workspace_id, path in self.active_workspaces.items()
        ]


# Global workspace manager instance
_workspace_manager: Optional[WorkspaceManager] = None


def get_workspace_manager() -> WorkspaceManager:
    """Get the global workspace manager instance"""
    global _workspace_manager
    if _workspace_manager is None:
        _workspace_manager = WorkspaceManager()
    return _workspace_manager
