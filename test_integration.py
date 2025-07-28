#!/usr/bin/env python3
"""
test_integration.py - Simple integration test to verify the system works
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.config import get_config
from src.core.logging import get_logger, setup_logging
from src.claude.cli_interface import ClaudeSubAgentInterface
from src.claude.workspace_manager import get_workspace_manager


async def test_basic_claude_execution():
    """Test basic Claude execution"""
    print("\n1. Testing basic Claude execution...")
    
    interface = ClaudeSubAgentInterface()
    result = await interface.execute(
        "Say 'Integration test successful'",
        timeout=30
    )
    
    if result.success:
        print(f"   ✓ Claude responded: {result.output.strip()[:100]}")
        return True
    else:
        print(f"   ✗ Claude failed: {result.error}")
        return False


async def test_workspace_creation():
    """Test workspace creation"""
    print("\n2. Testing workspace creation...")
    
    manager = get_workspace_manager()
    
    async with manager.isolated_workspace("test-agent") as workspace:
        print(f"   ✓ Created workspace: {workspace}")
        
        # Check if .claude/agents exists
        agents_dir = workspace / ".claude" / "agents"
        if agents_dir.exists():
            print(f"   ✓ Agents directory exists")
            agent_count = len(list(agents_dir.glob("*.md")))
            print(f"   ✓ Found {agent_count} agent definitions")
        else:
            print(f"   ✗ Agents directory missing")
            return False
    
    print(f"   ✓ Workspace cleaned up")
    return True


async def test_sub_agent_execution():
    """Test sub-agent execution if test-agent exists"""
    print("\n3. Testing sub-agent execution...")
    
    interface = ClaudeSubAgentInterface()
    
    # Check if test-agent exists
    if not interface.verify_agent_exists("test-agent"):
        print("   ⚠ test-agent not found, skipping sub-agent test")
        print("   Create ~/.claude/agents/test-agent.md to enable this test")
        return True  # Not a failure, just skipped
    
    # Test with workspace isolation
    manager = get_workspace_manager()
    
    async with manager.isolated_workspace("test-agent") as workspace:
        result = await interface.execute_with_agent(
            "test-agent",
            "explain what you are",
            workspace=workspace,
            timeout=30
        )
        
        if result.success:
            print(f"   ✓ Sub-agent responded: {result.output.strip()[:100]}")
            return True
        else:
            print(f"   ✗ Sub-agent failed: {result.error}")
            return False


async def test_concurrent_execution():
    """Test concurrent execution with rate limiting"""
    print("\n4. Testing concurrent execution...")
    
    interface = ClaudeSubAgentInterface()
    config = get_config()
    
    # Create multiple simple prompts
    prompts = [
        ("Say 'First'", None),
        ("Say 'Second'", None),
        ("Say 'Third'", None),
    ]
    
    print(f"   Running {len(prompts)} prompts with max_concurrent={config.claude.max_concurrent}")
    
    results = await interface.execute_batch(prompts)
    
    success_count = sum(1 for r in results if not isinstance(r, Exception) and r.success)
    print(f"   ✓ Completed {success_count}/{len(prompts)} successfully")
    
    return success_count == len(prompts)


async def test_configuration():
    """Test configuration system"""
    print("\n5. Testing configuration...")
    
    config = get_config()
    
    print(f"   ✓ Claude CLI path: {config.claude.cli_path}")
    print(f"   ✓ Max concurrent: {config.claude.max_concurrent}")
    print(f"   ✓ Token budget: {config.tokens.daily_budget}")
    print(f"   ✓ Use worktrees: {config.workspace.use_worktrees}")
    
    return True


async def main():
    """Run all integration tests"""
    print("="*60)
    print("Headless Research System - Integration Test")
    print("="*60)
    
    # Setup logging
    setup_logging()
    logger = get_logger("integration_test")
    
    # Get configuration
    config = get_config()
    
    if config.dry_run:
        print("\n⚠️  Running in DRY RUN mode - Claude commands will be simulated")
    
    tests = [
        ("Configuration", test_configuration),
        ("Basic Claude Execution", test_basic_claude_execution),
        ("Workspace Creation", test_workspace_creation),
        ("Sub-agent Execution", test_sub_agent_execution),
        ("Concurrent Execution", test_concurrent_execution),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if await test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n✗ {test_name} failed with exception: {e}")
            logger.error(f"Test failed: {test_name}", exc_info=True)
            failed += 1
    
    # Cleanup
    manager = get_workspace_manager()
    await manager.cleanup_all()
    
    # Summary
    print("\n" + "="*60)
    print(f"Tests passed: {passed}/{len(tests)}")
    
    if failed == 0:
        print("\n✅ All tests passed! System is ready.")
        return 0
    else:
        print(f"\n❌ {failed} tests failed. Check the errors above.")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTest interrupted.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        sys.exit(1)
