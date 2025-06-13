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
TARGET_DIR="/usr/local/bin"
# Use local bin if not running as root
if [ "$(id -u)" -ne 0 ]; then
    TARGET_DIR="${HOME}/.local/bin"
    mkdir -p "${TARGET_DIR}"
    export PATH="${TARGET_DIR}:${PATH}"
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
else
    log_warn "kubectl installation completed but could not be found in PATH"
    echo "Please add ${TARGET_DIR} to your PATH"
    echo "export PATH=\"${TARGET_DIR}:\${PATH}\"" >> ~/.bashrc
    echo "export PATH=\"${TARGET_DIR}:\${PATH}\"" >> ~/.zshrc
fi
