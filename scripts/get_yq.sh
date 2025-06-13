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

# Check if yq is already installed
if command -v yq &> /dev/null; then
    log_info "yq is already installed at $(which yq)"
    yq --version
    exit 0
fi

# Determine the target directory
TARGET_DIR="${HOME}/.local/bin"
mkdir -p "${TARGET_DIR}"

# Add target directory to PATH if not already present
if ! echo ":${PATH}:" | grep -q ":${TARGET_DIR}:"; then
    export PATH="${TARGET_DIR}:${PATH}"
    log_info "Added ${TARGET_DIR} to PATH for this session"
fi

# Determine OS and architecture
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
case $(uname -m) in
    x86_64) ARCH="amd64" ;;
    arm64|aarch64) ARCH="arm64" ;;
    *) log_error "Unsupported architecture: $(uname -m)" ;;
esac

# Download URL
VERSION="v4.45.4"
DOWNLOAD_URL="https://github.com/mikefarah/yq/releases/download/${VERSION}/yq_${OS}_${ARCH}"

log_info "Downloading yq ${VERSION} for ${OS}/${ARCH}..."
if ! curl -sL "${DOWNLOAD_URL}" -o "${TARGET_DIR}/yq"; then
    log_error "Failed to download yq from ${DOWNLOAD_URL}"
fi

# Make it executable
chmod +x "${TARGET_DIR}/yq"

# Verify installation
if command -v yq &> /dev/null; then
    log_info "yq installed successfully!"
    yq --version
    
    # Update shell config if not in PATH
    if ! echo ":${PATH}:" | grep -q ":${TARGET_DIR}:"; then
        log_warn "${TARGET_DIR} is not in your PATH"
        echo "Add the following to your shell profile (~/.bashrc, ~/.zshrc, etc.):"
        echo "  export PATH=\"${TARGET_DIR}:\$PATH\""
    fi
else
    log_error "yq installation failed"
fi
