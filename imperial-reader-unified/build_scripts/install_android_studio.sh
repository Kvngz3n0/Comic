#!/bin/bash
# =============================================================================
# Imperial Reader - Android Studio Installer
# Auto-detects OS and installs Android Studio with all dependencies
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

OS=""
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="mac"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
    OS="windows"
else
    log_err "Unsupported OS: $OSTYPE"
    exit 1
fi

log_info "Detected OS: $OS"

# =============================================================================
# STEP 1: Install Java (OpenJDK 17)
# =============================================================================
install_java() {
    log_info "Installing OpenJDK 17..."

    if command -v java &> /dev/null; then
        JAVA_VER=$(java -version 2>&1 | head -n 1 | cut -d'"' -f2)
        log_ok "Java found: $JAVA_VER"
        if [[ "$JAVA_VER" == 17* || "$JAVA_VER" == 21* ]]; then
            log_ok "Java version is compatible."
            return
        else
            log_warn "Java version $JAVA_VER may not be compatible. Need 17 or 21."
        fi
    fi

    if [ "$OS" == "linux" ]; then
        if command -v apt-get &> /dev/null; then
            sudo apt-get update
            sudo apt-get install -y openjdk-17-jdk || {
                log_warn "apt install failed, trying snap..."
                sudo snap install openjdk --classic
            }
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y java-17-openjdk-devel
        elif command -v pacman &> /dev/null; then
            sudo pacman -S --noconfirm jdk17-openjdk
        else
            log_err "No supported package manager found. Please install OpenJDK 17 manually."
            exit 1
        fi
    elif [ "$OS" == "mac" ]; then
        if command -v brew &> /dev/null; then
            brew install openjdk@17
        else
            log_err "Homebrew not found. Install from https://brew.sh first."
            exit 1
        fi
    fi

    log_ok "Java installed."
}

# =============================================================================
# STEP 2: Install Android Studio
# =============================================================================
install_android_studio() {
    log_info "Installing Android Studio..."

    if command -v studio.sh &> /dev/null || [ -d "/opt/android-studio" ] || [ -d "$HOME/android-studio" ]; then
        log_ok "Android Studio already installed."
        return
    fi

    if [ "$OS" == "linux" ]; then
        # Download Android Studio
        STUDIO_URL="https://redirector.gvt1.com/edgedl/android/studio/ide-zips/2023.1.1.28/android-studio-2023.1.1.28-linux.tar.gz"
        TEMP_DIR=$(mktemp -d)

        log_info "Downloading Android Studio..."
        wget -q --show-progress "$STUDIO_URL" -O "$TEMP_DIR/android-studio.tar.gz" || {
            log_warn "wget failed, trying curl..."
            curl -L "$STUDIO_URL" -o "$TEMP_DIR/android-studio.tar.gz"
        }

        log_info "Extracting..."
        sudo tar -xzf "$TEMP_DIR/android-studio.tar.gz" -C /opt/ || {
            log_warn "Cannot extract to /opt, using home directory..."
            tar -xzf "$TEMP_DIR/android-studio.tar.gz" -C "$HOME/"
        }

        rm -rf "$TEMP_DIR"

        # Create desktop entry
        if [ -d "/opt/android-studio" ]; then
            sudo ln -sf /opt/android-studio/bin/studio.sh /usr/local/bin/studio
        else
            ln -sf "$HOME/android-studio/bin/studio.sh" "$HOME/.local/bin/studio" 2>/dev/null || true
        fi

    elif [ "$OS" == "mac" ]; then
        if command -v brew &> /dev/null; then
            brew install --cask android-studio
        else
            log_err "Please install Android Studio manually from https://developer.android.com/studio"
            exit 1
        fi
    fi

    log_ok "Android Studio installed."
}

# =============================================================================
# STEP 3: Install Android SDK & Build Tools
# =============================================================================
install_sdk() {
    log_info "Setting up Android SDK..."

    # Find SDK path
    if [ -d "$HOME/Android/Sdk" ]; then
        SDK_DIR="$HOME/Android/Sdk"
    elif [ -d "$HOME/Library/Android/sdk" ]; then
        SDK_DIR="$HOME/Library/Android/sdk"
    else
        SDK_DIR="$HOME/android-sdk"
        mkdir -p "$SDK_DIR"
    fi

    export ANDROID_SDK_ROOT="$SDK_DIR"
    export ANDROID_HOME="$SDK_DIR"

    # Download command line tools
    if [ ! -d "$SDK_DIR/cmdline-tools" ]; then
        log_info "Downloading SDK command line tools..."
        CMDLINE_URL="https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip"
        TEMP_DIR=$(mktemp -d)
        wget -q "$CMDLINE_URL" -O "$TEMP_DIR/cmdline.zip" || curl -L "$CMDLINE_URL" -o "$TEMP_DIR/cmdline.zip"
        unzip -q "$TEMP_DIR/cmdline.zip" -d "$SDK_DIR/"
        mkdir -p "$SDK_DIR/cmdline-tools/latest"
        mv "$SDK_DIR/cmdline-tools/bin" "$SDK_DIR/cmdline-tools/latest/" 2>/dev/null || true
        mv "$SDK_DIR/cmdline-tools/lib" "$SDK_DIR/cmdline-tools/latest/" 2>/dev/null || true
        rm -rf "$TEMP_DIR"
    fi

    # Install required SDK components
    if [ -d "$SDK_DIR/cmdline-tools/latest/bin" ]; then
        log_info "Installing SDK platforms and build tools..."
        yes | "$SDK_DIR/cmdline-tools/latest/bin/sdkmanager" --licenses 2>/dev/null || true
        "$SDK_DIR/cmdline-tools/latest/bin/sdkmanager"             "platforms;android-34"             "build-tools;34.0.0"             "platform-tools"             "ndk;25.2.9519653" 2>/dev/null || {
            log_warn "Some SDK components failed to install. Will retry with basic set."
            "$SDK_DIR/cmdline-tools/latest/bin/sdkmanager"                 "platforms;android-34"                 "build-tools;34.0.0"                 "platform-tools"
        }
    fi

    # Add to PATH
    SHELL_RC=""
    if [ -f "$HOME/.bashrc" ]; then SHELL_RC="$HOME/.bashrc"; fi
    if [ -f "$HOME/.zshrc" ]; then SHELL_RC="$HOME/.zshrc"; fi

    if [ -n "$SHELL_RC" ]; then
        if ! grep -q "ANDROID_SDK_ROOT" "$SHELL_RC"; then
            echo "" >> "$SHELL_RC"
            echo "# Android SDK" >> "$SHELL_RC"
            echo "export ANDROID_SDK_ROOT=\"$SDK_DIR\"" >> "$SHELL_RC"
            echo "export ANDROID_HOME=\"$SDK_DIR\"" >> "$SHELL_RC"
            echo "export PATH=\"\$PATH:\$ANDROID_SDK_ROOT/platform-tools:\$ANDROID_SDK_ROOT/cmdline-tools/latest/bin\"" >> "$SHELL_RC"
            log_ok "Added Android SDK to $SHELL_RC"
        fi
    fi

    log_ok "Android SDK setup complete."
}

# =============================================================================
# STEP 4: Install Python dependencies for Kivy/Android
# =============================================================================
install_python_deps() {
    log_info "Installing Python build dependencies..."

    if [ "$OS" == "linux" ]; then
        sudo apt-get install -y python3-pip python3-venv             libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev             libportmidi-dev libswscale-dev libavformat-dev libavcodec-dev             libfreetype6-dev libgl1-mesa-dev libgles2-mesa-dev             libgstreamer1.0-dev gstreamer1.0-plugins-base             libjpeg-dev zlib1g-dev 2>/dev/null || {
            log_warn "Some packages failed, continuing..."
        }
    fi

    pip3 install --user buildozer cython pillow 2>/dev/null || {
        log_warn "pip install failed, trying with --break-system-packages..."
        pip3 install --user --break-system-packages buildozer cython pillow 2>/dev/null || true
    }

    log_ok "Python dependencies installed."
}

# =============================================================================
# MAIN
# =============================================================================
echo ""
echo "============================================================"
echo "  Imperial Reader - Android Studio & SDK Installer"
echo "============================================================"
echo ""

install_java
install_android_studio
install_sdk
install_python_deps

echo ""
echo "============================================================"
log_ok "Installation complete!"
echo ""
echo "Next steps:"
echo "  1. Restart your terminal or run: source ~/.bashrc"
echo "  2. Run: ./build_scripts/build_android.sh"
echo "============================================================"
