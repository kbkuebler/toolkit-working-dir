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

# Check if kubectl is already installed
if command -v kubectl &> /dev/null; then
    log_info "kubectl is already installed at $(which kubectl)"
    kubectl version --client --short
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

# Get the latest stable version
LATEST_VERSION=$(curl -L -s https://dl.k8s.io/release/stable.txt)
if [ -z "$LATEST_VERSION" ]; then
    log_warn "Failed to fetch latest kubectl version, using v1.29.0 as fallback"
    LATEST_VERSION="v1.29.0"
fi

# Determine OS and architecture
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
case $(uname -m) in
    x86_64) ARCH=amd64 ;;
    arm64|aarch64) ARCH=arm64 ;;
    *) log_error "Unsupported architecture: $(uname -m)" ;;
esac

# Download URL
DOWNLOAD_URL="https://dl.k8s.io/release/${LATEST_VERSION}/bin/${OS}/${ARCH}/kubectl"

log_info "Downloading kubectl ${LATEST_VERSION} for ${OS}/${ARCH}..."
curl -L "${DOWNLOAD_URL}" -o "${TARGET_DIR}/kubectl" || \
    log_error "Failed to download kubectl from ${DOWNLOAD_URL}"

# Make it executable
chmod +x "${TARGET_DIR}/kubectl"

# Verify installation
if command -v kubectl &> /dev/null; then
    log_info "kubectl installed successfully!"
    kubectl version --client --short
    
    # Update shell config if not in PATH
    if ! echo ":${PATH}:" | grep -q ":${TARGET_DIR}:"; then
        log_warn "${TARGET_DIR} is not in your PATH"
        echo "Add the following to your shell profile (~/.bashrc, ~/.zshrc, etc.):"
        echo "  export PATH=\"${TARGET_DIR}:\$PATH\""
    fi
else
    log_error "kubectl installation failed"
fi
