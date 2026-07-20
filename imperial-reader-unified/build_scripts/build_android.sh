#!/bin/bash
# =============================================================================
# Imperial Reader - Android Build Script
# Uses Buildozer to create APK
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
echo "  Imperial Reader - Android Build"
echo "============================================================"
echo ""

# Check buildozer
if ! command -v buildozer &> /dev/null; then
    log_err "Buildozer not found. Run ./install_android_studio.sh first."
    exit 1
fi

# Create buildozer.spec if not exists
if [ ! -f "buildozer.spec" ]; then
    log_info "Creating buildozer.spec..."

    cat > buildozer.spec << 'EOF'
[app]
title = Imperial Reader
package.name = imperialreader
package.domain = com.imperialreader
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,json,xml,txt
version = 1.0
requirements = python3,kivy==2.3.0,kivymd==1.1.1,requests,urllib3,Pillow,beautifulsoup4,lxml,pysocks
orientation = portrait
fullscreen = 0
android.api = 34
android.minapi = 28
android.ndk = 25.2.9519653
android.sdk = 34
android.arch = arm64-v8a
android.permissions = INTERNET,ACCESS_NETWORK_STATE,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.wakelock = True
android.presplash_color = #0A0A0A
android.add_src = src/

[buildozer]
log_level = 2
warn_on_root = 1
EOF
    log_ok "buildozer.spec created."
fi

# Create buildozer directory structure
mkdir -p .buildozer/android/platform

# Build debug APK
log_info "Building Android APK (this may take 15-30 minutes first time)..."
echo ""

buildozer android debug 2>&1 | tee build.log || {
    log_err "Build failed. Checking common issues..."

    if grep -q "No module named 'buildozer'" build.log 2>/dev/null; then
        log_err "Buildozer not installed. Run: pip install buildozer"
        exit 1
    fi

    if grep -q "NDK is not installed" build.log 2>/dev/null; then
        log_err "Android NDK not found. Run: ./install_android_studio.sh"
        exit 1
    fi

    if grep -q "JAVA_HOME" build.log 2>/dev/null; then
        log_err "JAVA_HOME not set. Run: export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64"
        exit 1
    fi

    log_err "Unknown build error. Check build.log for details."
    exit 1
}

# Find APK
APK_PATH=$(find bin -name "*.apk" | head -n 1)
if [ -n "$APK_PATH" ]; then
    log_ok "APK built successfully!"
    log_ok "Location: $PROJECT_DIR/$APK_PATH"
    echo ""
    echo "Install with: adb install $APK_PATH"
else
    log_err "APK not found in bin/ directory."
    exit 1
fi
