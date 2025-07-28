#!/usr/bin/env python3
"""
scripts/check_setup.py

Verify the headless research environment is properly configured.
Run this before starting development or deployment.
"""

import sys
import subprocess
import shutil
from pathlib import Path
import asyncio

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import ResearchConfig
from src.claude.cli_interface import ClaudeInterface


class SetupChecker:
    """Check system setup and dependencies"""
    
    def __init__(self):
        self.checks_passed = 0
        self.checks_failed = 0
        self.warnings = []
    
    def print_header(self, text: str):
        print(f"\n{'='*60}")
        print(f"  {text}")
        print(f"{'='*60}\n")
    
    def print_check(self, name: str, passed: bool, message: str = ""):
        symbol = "✓" if passed else "✗"
        color = "\033[92m" if passed else "\033[91m"
        reset = "\033[0m"
        
        print(f"{color}[{symbol}]{reset} {name}")
        if message:
            print(f"    {message}")
        
        if passed:
            self.checks_passed += 1
        else:
            self.checks_failed += 1
    
    def print_warning(self, message: str):
        print(f"\033[93m[!]\033[0m {message}")
        self.warnings.append(message)
    
    def check_python_version(self):
        """Check Python version"""
        version = sys.version_info
        passed = version >= (3, 8)
        self.print_check(
            "Python version",
            passed,
            f"Python {version.major}.{version.minor}.{version.micro}"
        )
        return passed
    
    def check_claude_cli(self):
        """Check Claude CLI installation"""
        claude_path = shutil.which("claude")
        
        if not claude_path:
            self.print_check("Claude CLI", False, "Not found in PATH")
            return False
        
        try:
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                version = result.stdout.strip()
                self.print_check("Claude CLI", True, f"Found at {claude_path} - {version}")
                
                # Check for -p flag support
                help_result = subprocess.run(
                    ["claude", "--help"],
                    capture_output=True,
                    text=True
                )
                
                if "-p" in help_result.stdout:
                    self.print_check("Claude -p flag", True, "Headless mode supported")
                else:
                    self.print_check("Claude -p flag", False, "Headless mode not found in help")
                
                return True
            else:
                self.print_check("Claude CLI", False, f"Version check failed: {result.stderr}")
                return False
                
        except Exception as e:
            self.print_check("Claude CLI", False, f"Error: {e}")
            return False
    
    def check_git(self):
        """Check git installation and repo status"""
        git_path = shutil.which("git")
        
        if not git_path:
            self.print_check("Git", False, "Not found in PATH")
            self.print_warning("Git worktrees will not be available")
            return False
        
        self.print_check("Git", True, f"Found at {git_path}")
        
        # Check if we're in a git repo
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self.print_check("Git repository", True, "Current directory is a git repo")
                
                # Check for uncommitted changes
                status_result = subprocess.run(
                    ["git", "status", "--porcelain"],
                    capture_output=True,
                    text=True
                )
                
                if status_result.stdout.strip():
                    self.print_warning("Uncommitted changes detected - worktrees may have conflicts")
                
                return True
            else:
                self.print_check("Git repository", False, "Not in a git repository")
                self.print_warning("Git worktrees will not be available")
                return False
                
        except Exception as e:
            self.print_check("Git check", False, f"Error: {e}")
            return False
    
    def check_directories(self):
        """Check required directories"""
        config = ResearchConfig()
        
        directories = [
            ("Agent directory", config.agent_dir),
            ("Cache directory", config.cache.cache_dir),
            ("Log directory", config.logging.log_dir),
            ("Workspace directory", config.workspace.base_dir)
        ]
        
        all_good = True
        for name, path in directories:
            if path.exists():
                self.print_check(name, True, str(path))
            else:
                try:
                    path.mkdir(parents=True, exist_ok=True)
                    self.print_check(name, True, f"Created: {path}")
                except Exception as e:
                    self.print_check(name, False, f"Cannot create: {e}")
                    all_good = False
        
        return all_good
    
    def check_agents(self):
        """Check for agent definitions"""
        config = ResearchConfig()
        agent_files = list(config.agent_dir.glob("*.md"))
        
        if not config.agent_dir.exists():
            self.print_check("Agent definitions", False, f"Directory not found: {config.agent_dir}")
            return False
        
        if agent_files:
            self.print_check(
                "Agent definitions",
                True,
                f"Found {len(agent_files)} agents"
            )
            for agent in agent_files[:5]:  # Show first 5
                print(f"    - {agent.stem}")
            if len(agent_files) > 5:
                print(f"    ... and {len(agent_files) - 5} more")
            return True
        else:
            self.print_check(
                "Agent definitions",
                False,
                "No agent definitions found"
            )
            self.print_warning(f"Create .md files in {config.agent_dir}")
            return False
    
    async def check_claude_execution(self):
        """Test Claude execution"""
        try:
            interface = ClaudeInterface()
            
            # Test basic execution - use await directly
            result = await interface.execute(
                "Say 'Setup test successful'",
                timeout=30
            )
            
            if result.success and "successful" in result.output:
                self.print_check(
                    "Claude execution",
                    True,
                    "Basic prompt execution works"
                )
                
                # Test sub-agent if available
                if Path.home().joinpath(".claude/agents/test-agent.md").exists():
                    result = await interface.execute(
                        "Use test-agent to say hello",
                        timeout=30
                    )
                    
                    if result.success:
                        self.print_check(
                            "Sub-agent execution",
                            True,
                            "Sub-agent invocation works"
                        )
                    else:
                        self.print_check(
                            "Sub-agent execution",
                            False,
                            "Sub-agent invocation failed"
                        )
                
                return True
            else:
                self.print_check(
                    "Claude execution",
                    False,
                    f"Unexpected output: {result.output[:100]}"
                )
                return False
                
        except Exception as e:
            self.print_check("Claude execution", False, f"Error: {e}")
            return False
    
    def check_environment_variables(self):
        """Check environment variables"""
        import os
        
        env_vars = [
            ("CLAUDE_CLI_PATH", "claude"),
            ("TOKEN_DAILY_BUDGET", "100000"),
            ("CLAUDE_MAX_CONCURRENT", "3"),
        ]
        
        self.print_check("Environment variables", True, "Checking configuration")
        
        for var, default in env_vars:
            value = os.getenv(var, default)
            if os.getenv(var):
                print(f"    {var}={value}")
            else:
                print(f"    {var}={value} (default)")
    
    async def run_all_checks(self):
        """Run all setup checks"""
        
        self.print_header("Headless Research Setup Check")
        
        # Basic checks
        self.check_python_version()
        self.check_claude_cli()
        self.check_git()
        self.check_directories()
        self.check_agents()
        self.check_environment_variables()
        
        # Execution test
        if self.checks_failed == 0:
            self.print_header("Testing Claude Execution")
            await self.check_claude_execution()
        
        # Summary
        self.print_header("Summary")
        
        total = self.checks_passed + self.checks_failed
        print(f"Checks passed: {self.checks_passed}/{total}")
        
        if self.warnings:
            print(f"\nWarnings ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  - {warning}")
        
        if self.checks_failed > 0:
            print("\n❌ Setup incomplete. Fix the failed checks above.")
            return False
        else:
            print("\n✅ Setup complete! Ready for headless research.")
            return True


def main():
    """Run setup checker"""
    checker = SetupChecker()
    
    try:
        success = asyncio.run(checker.run_all_checks())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nSetup check interrupted.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup check failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
