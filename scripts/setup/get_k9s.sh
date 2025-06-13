#!/bin/bash
set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print info messages
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

# Function to print warning messages
log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Function to print error messages and exit
log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Check if k9s is already installed
if command -v k9s &> /dev/null; then
    log_info "k9s is already installed at $(which k9s)"
    k9s version
    exit 0
fi

# Determine the target directory
TARGET_DIR="/usr/local/bin"

# Add target directory to PATH if not already present
if ! echo ":${PATH}:" | grep -q ":${TARGET_DIR}:"; then
    export PATH="${TARGET_DIR}:${PATH}"
    log_info "Added ${TARGET_DIR} to PATH for this session"
fi

# Detect OS and architecture
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

# Map architecture to k9s format
case $ARCH in
    x86_64) ARCH="amd64" ;;
    aarch64) ARCH="arm64" ;;
    armv7*) ARCH="arm" ;;
    *) log_error "Unsupported architecture: $ARCH" ;;
esac

# Get latest k9s version
LATEST_VERSION=$(curl -s https://api.github.com/repos/derailed/k9s/releases/latest | grep 'tag_name' | cut -d '"' -f 4)
if [ -z "$LATEST_VERSION" ]; then
    log_warn "Failed to fetch latest k9s version, using v0.32.4 as fallback"
    LATEST_VERSION="v0.32.4"
fi

# Download URL
DOWNLOAD_URL="https://github.com/derailed/k9s/releases/download/${LATEST_VERSION}/k9s_${OS}_${ARCH}.tar.gz"
TEMP_DIR=$(mktemp -d)

log_info "Downloading k9s ${LATEST_VERSION} for ${OS}/${ARCH}..."
curl -sL "${DOWNLOAD_URL}" -o "${TEMP_DIR}/k9s.tar.gz" || \
    log_error "Failed to download k9s from ${DOWNLOAD_URL}"

# Extract and install
log_info "Installing k9s to ${TARGET_DIR}..."
tar -xzf "${TEMP_DIR}/k9s.tar.gz" -C "${TEMP_DIR}" k9s
chmod +x "${TEMP_DIR}/k9s"
mv "${TEMP_DIR}/k9s" "${TARGET_DIR}/k9s"

# Cleanup
rm -rf "${TEMP_DIR}"

# Verify installation
if command -v k9s &> /dev/null; then
    log_info "k9s installed successfully!"
    k9s version
    
    # Update shell config if not in PATH
    if ! echo ":${PATH}:" | grep -q ":${TARGET_DIR}:"; then
        log_warn "${TARGET_DIR} is not in your PATH"
        echo "Add the following to your shell profile (~/.bashrc, ~/.zshrc, etc.):"
        echo "  export PATH=\"${TARGET_DIR}:\$PATH\""
    fi
else
    log_error "k9s installation failed"
fi
