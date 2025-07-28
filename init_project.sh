#!/bin/bash
# init_project.sh - Initialize the headless research project structure

set -e

echo "🚀 Initializing Headless Research Project"
echo "========================================"

# Create directory structure
echo "📁 Creating directory structure..."
mkdir -p src/{core,claude,agents,orchestration,extraction,utils}
mkdir -p src/agents/definitions
mkdir -p tests/fixtures
mkdir -p scripts
mkdir -p logs
mkdir -p ~/.claude/agents

# Create __init__.py files
echo "📄 Creating __init__.py files..."
touch src/__init__.py
touch src/core/__init__.py
touch src/claude/__init__.py
touch src/agents/__init__.py
touch src/orchestration/__init__.py
touch src/extraction/__init__.py
touch src/utils/__init__.py
touch tests/__init__.py

# Copy .env.example to .env if it doesn't exist
if [ ! -f .env ]; then
    echo "⚙️  Creating .env from template..."
    cp .env.example .env
    echo "   ✓ Created .env (update with your settings)"
else
    echo "   ℹ️  .env already exists"
fi

# Create a simple test agent
echo "🤖 Creating test agent..."
cat > ~/.claude/agents/test-agent.md << 'EOF'
---
name: test-agent
description: Simple test agent for verification
tools: read
---

You are a test agent for the headless research system.

When invoked, always start your response with:
"TEST AGENT ACTIVE: I am a test agent for verification purposes."

Then respond to the user's query concisely.
EOF
echo "   ✓ Created test-agent in ~/.claude/agents/"

# Create .gitignore if it doesn't exist
if [ ! -f .gitignore ]; then
    echo "📝 Creating .gitignore..."
    cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.env

# Logs
logs/
*.log

# Cache
.cache/
*.cache

# Research outputs
results/
workspaces/
.research_cache/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Project specific
/tmp/
/research_workspaces/
EOF
fi

# Make scripts executable
echo "🔧 Setting permissions..."
chmod +x scripts/check_setup.py 2>/dev/null || true
chmod +x test_integration.py 2>/dev/null || true

# Install dependencies
echo ""
echo "📦 Ready to install dependencies!"
echo "Run the following commands:"
echo ""
echo "  # Create virtual environment"
echo "  python3 -m venv venv"
echo "  source venv/bin/activate  # On Windows: venv\\Scripts\\activate"
echo ""
echo "  # Install dependencies"
echo "  pip install -r requirements.txt"
echo ""
echo "  # Verify setup"
echo "  python scripts/check_setup.py"
echo ""
echo "  # Run integration test"
echo "  python test_integration.py"
echo ""
echo "✅ Project structure created successfully!"
