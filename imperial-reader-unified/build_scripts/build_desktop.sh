#!/bin/bash
# =============================================================================
# Imperial Reader - Desktop Build Script
# Builds and runs on Linux/macOS/Windows desktop
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_err() { echo -e "${RED}[ERROR]${NC} $1"; }

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

echo ""
echo "============================================================"
echo "  Imperial Reader - Desktop Build"
echo "============================================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    log_err "Python 3 not found. Please install Python 3.8+."
    exit 1
fi

PYTHON_VER=$(python3 --version 2>&1 | cut -d' ' -f2)
log_info "Python version: $PYTHON_VER"

# Create virtual environment if not exists
VENV_DIR="$PROJECT_DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
    log_info "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate venv
source "$VENV_DIR/bin/activate" 2>/dev/null || source "$VENV_DIR/Scripts/activate" 2>/dev/null

# Upgrade pip
log_info "Upgrading pip..."
pip install --upgrade pip wheel setuptools 2>/dev/null || {
    log_warn "pip upgrade failed, continuing..."
}

# Install requirements
log_info "Installing dependencies..."
pip install -r requirements.txt 2>/dev/null || {
    log_warn "Some packages failed, retrying individually..."
    pip install kivy kivymd requests beautifulsoup4 lxml pillow pysocks
}

log_ok "Dependencies installed."

# Run the app
echo ""
echo "============================================================"
log_ok "Starting Imperial Reader..."
echo "============================================================"
echo ""

python3 main.py
