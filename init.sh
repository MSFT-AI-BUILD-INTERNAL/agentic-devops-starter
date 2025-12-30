#!/bin/bash
set -e

echo "🚀 Initializing development environment..."

# Install uv if not already installed
if ! command -v uv &> /dev/null; then
    echo "📦 Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

# Create virtual environment
echo "🐍 Creating virtual environment..."
uv venv --clear

# Activate virtual environment
if [ ! -f ".venv/bin/activate" ]; then
    echo "❌ Failed to locate virtual environment activation script at .venv/bin/activate"
    echo "   Ensure that 'uv venv' created the environment successfully."
    exit 1
fi
source .venv/bin/activate

# Install Python packages from pyproject.toml
echo "📚 Installing Python packages..."
uv pip install -e .

# Install specify-cli
echo "🔧 Installing specify-cli..."
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git

# Initialize specify with copilot
echo "🤖 Initializing AI environment with copilot..."
specify init . --ai copilot --force

specify check

echo "✓ Speckit environment initialized successfully."

echo ""
echo "✨ Installation complete!"
echo ""
echo "📝 Installed packages:"
echo "   - agent-framework"
echo "   - specify-cli"
echo ""
echo "🤖 AI Environment:"
echo "   - Initialized with GitHub Copilot"
echo ""
echo "🎯 To activate the virtual environment, run:"
echo "   source .venv/bin/activate"
