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
uv pip install -e ./app --prerelease=allow

# Install specify-cli
echo "🔧 Installing specify-cli..."
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git

# Initialize specify with copilot
echo "🤖 Initializing AI environment with copilot..."
specify init . --ai copilot --force

specify check

echo "✓ Speckit environment initialized successfully."

# Install Terraform
if ! command -v terraform &> /dev/null; then
    echo "🏗️  Installing Terraform..."
    
    # Detect architecture
    ARCH=$(uname -m)
    if [ "$ARCH" = "x86_64" ]; then
        TF_ARCH="amd64"
    elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
        TF_ARCH="arm64"
    else
        echo "❌ Unsupported architecture: $ARCH"
        exit 1
    fi
    
    # Download and install latest Terraform
    TF_VERSION=$(curl -s https://checkpoint-api.hashicorp.com/v1/check/terraform | grep -o '"current_version":"[^"]*"' | cut -d'"' -f4)
    wget -q https://releases.hashicorp.com/terraform/${TF_VERSION}/terraform_${TF_VERSION}_linux_${TF_ARCH}.zip
    unzip -q terraform_${TF_VERSION}_linux_${TF_ARCH}.zip
    sudo mv terraform /usr/local/bin/
    rm terraform_${TF_VERSION}_linux_${TF_ARCH}.zip
    
    echo "✅ Terraform ${TF_VERSION} installed"
else
    echo "✅ Terraform already installed: $(terraform version | head -n1 | cut -d'v' -f2)"
fi

# Install kubectl
if ! command -v kubectl &> /dev/null; then
    echo "☸️  Installing kubectl..."
    
    # Download the latest stable version
    KUBECTL_VERSION=$(curl -L -s https://dl.k8s.io/release/stable.txt)
    curl -LO "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl"
    
    # Install kubectl
    sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
    rm kubectl
    
    echo "✅ kubectl ${KUBECTL_VERSION} installed"
else
    echo "✅ kubectl already installed: $(kubectl version --client --short 2>/dev/null | cut -d' ' -f3 || kubectl version --client 2>/dev/null | grep 'Client Version' | cut -d':' -f2 | tr -d ' ')"
fi

# Install Node.js and npm using nvm
export NVM_DIR="$HOME/.nvm"

if ! command -v node &> /dev/null; then
    echo "📦 Installing Node.js and npm via nvm..."
    
    # Install nvm
    if [ ! -d "$NVM_DIR" ]; then
        curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
    fi
    
    # Load nvm
    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
    [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"
    
    # Install latest LTS version of Node.js
    nvm install --lts
    nvm use --lts
    nvm alias default lts/*
    
    NODE_VERSION=$(node --version)
    NPM_VERSION=$(npm --version)
    echo "✅ Node.js ${NODE_VERSION} and npm ${NPM_VERSION} installed"
else
    # Load nvm even if node is already installed
    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
    
    NODE_VERSION=$(node --version)
    NPM_VERSION=$(npm --version)
    echo "✅ Node.js ${NODE_VERSION} and npm ${NPM_VERSION} already installed"
fi

# Add npm global bin to PATH
NPM_GLOBAL_BIN=$(npm config get prefix 2>/dev/null)/bin
if [ -d "$NPM_GLOBAL_BIN" ]; then
    export PATH="$NPM_GLOBAL_BIN:$PATH"
fi

# Install frontend dependencies if frontend directory exists
if [ -d "frontend" ]; then
    echo "📦 Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
    echo "✅ Frontend dependencies installed"
fi

echo ""
echo "✨ Installation complete!"
echo ""
echo "📝 Installed packages:"
echo "   - agent-framework"
echo "   - specify-cli"
echo "   - terraform $(terraform version 2>/dev/null | head -n1 | cut -d'v' -f2 || echo '')"
echo "   - kubectl $(kubectl version --client --short 2>/dev/null | cut -d' ' -f3 || echo '')"
echo "   - node $(node --version 2>/dev/null || echo '')"
echo "   - npm $(npm --version 2>/dev/null || echo '')"
echo ""
echo "🤖 AI Environment:"
echo "   - Initialized with GitHub Copilot"
echo ""
echo "🎯 To activate the virtual environment, run:"
echo "   source .venv/bin/activate"
echo ""
echo "💡 To load Node.js environment, run:"
echo "   export NVM_DIR=\"\$HOME/.nvm\""
echo "   [ -s \"\$NVM_DIR/nvm.sh\" ] && \\. \"\$NVM_DIR/nvm.sh\""
