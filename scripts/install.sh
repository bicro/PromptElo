#!/bin/bash
# PromptElo installation script

set -e

PROMPTELO_DIR="$HOME/.promptelo"

echo "📊 Installing PromptElo..."

# Create installation directory
mkdir -p "$PROMPTELO_DIR"
mkdir -p "$PROMPTELO_DIR/client"
mkdir -p "$PROMPTELO_DIR/skills/prompt-elo/templates"

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

# Copy client files
echo "  → Copying client files..."
cp "$REPO_DIR/client/"*.py "$PROMPTELO_DIR/client/"

# Copy skill files
echo "  → Copying skill files..."
cp "$REPO_DIR/skills/prompt-elo/SKILL.md" "$PROMPTELO_DIR/skills/prompt-elo/"
cp "$REPO_DIR/skills/prompt-elo/templates/report.html" "$PROMPTELO_DIR/skills/prompt-elo/templates/"

# Install Python dependencies
echo "  → Installing Python dependencies..."
if command -v pip3 &> /dev/null; then
    pip3 install --quiet httpx
elif command -v pip &> /dev/null; then
    pip install --quiet httpx
else
    echo "Warning: pip not found. Please install httpx manually: pip install httpx"
fi

# Create default config
if [ ! -f "$PROMPTELO_DIR/config.json" ]; then
    echo "  → Creating default configuration..."
    cat > "$PROMPTELO_DIR/config.json" << 'EOF'
{
  "server_url": "https://promptelo-api.onrender.com",
  "user_id": null,
  "timeout": 5.0
}
EOF
fi

echo ""
echo "✅ PromptElo installed successfully!"
echo ""
echo "Usage:"
echo "  • Elo badges will appear automatically on every prompt"
echo "  • Run /prompt-elo for detailed analysis"
echo ""
echo "Configuration:"
echo "  • Edit $PROMPTELO_DIR/config.json to customize settings"
echo "  • Set PROMPTELO_SERVER_URL env var for custom server"
echo ""
