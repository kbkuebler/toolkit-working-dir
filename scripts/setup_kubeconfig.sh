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

# Check if running as root, and if not, re-run with sudo if possible
if [ "$(id -u)" -ne 0 ]; then
    # If we're being run non-interactively (like from bootstrap), just error out
    if [ ! -t 1 ]; then
        log_error "This script needs to be run as root"
    fi
    # If we're in a terminal, prompt for sudo
    exec sudo -E "$0" "$@"
    exit $?
fi

# Get the non-root user (assuming the user who invoked sudo)
if [ -z "${SUDO_USER:-}" ]; then
    log_error "This script must be run with sudo"
fi
USER_HOME=$(getent passwd "$SUDO_USER" | cut -d: -f6)
KUBE_DIR="$USER_HOME/.kube"
KUBE_CONFIG="$KUBE_DIR/k3s.yaml"
K3S_CONFIG="/etc/rancher/k3s/k3s.yaml"

# Check if k3s config exists
if [ ! -f "$K3S_CONFIG" ]; then
    log_error "k3s config not found at $K3S_CONFIG. Is k3s installed?"
fi

# Create .kube directory if it doesn't exist
log_info "Creating $KUBE_DIR if it doesn't exist"
mkdir -p "$KUBE_DIR"
chown "$SUDO_USER:$SUDO_USER" "$KUBE_DIR"
chmod 700 "$KUBE_DIR"

# Copy kubeconfig
log_info "Copying kubeconfig to $KUBE_CONFIG"
cp "$K3S_CONFIG" "$KUBE_CONFIG"
chown "$SUDO_USER:$SUDO_USER" "$KUBE_CONFIG"
chmod 600 "$KUBE_CONFIG"

# Update server URL to use localhost if it's using a local IP
sed -i 's|server: https://127.0.0.1|server: https://localhost|g' "$KUBE_CONFIG"
sed -i 's|server: https://[0-9]\+\.[0-9]\+\.[0-9]\+\.[0-9]\+|server: https://localhost|g' "$KUBE_CONFIG"

# Test the configuration
log_info "Testing kubeconfig..."
if ! sudo -u "$SUDO_USER" KUBECONFIG="$KUBE_CONFIG" kubectl get nodes; then
    log_error "Failed to verify kubeconfig. Please check if k3s is running properly."
fi

# Add environment variable to shell profiles
SHELL_RC=""
if [ -f "$USER_HOME/.bashrc" ]; then
    SHELL_RC="$USER_HOME/.bashrc"
elif [ -f "$USER_HOME/.bash_profile" ]; then
    SHELL_RC="$USER_HOME/.bash_profile"
elif [ -f "$USER_HOME/.zshrc" ]; then
    SHELL_RC="$USER_HOME/.zshrc"
fi

if [ -n "$SHELL_RC" ]; then
    log_info "Updating $SHELL_RC with KUBECONFIG"
    
    # Remove any existing KUBECONFIG export
    sed -i '/export KUBECONFIG=.*/d' "$SHELL_RC"
    
    # Add new export
    echo -e "\n# Set KUBECONFIG for k3s" >> "$SHELL_RC"
    echo "export KUBECONFIG=\"$KUBE_CONFIG\"" >> "$SHELL_RC"
    
    # Set ownership
    chown "$SUDO_USER:$SUDO_USER" "$SHELL_RC"
    
    log_info "Added KUBECONFIG to $SHELL_RC"
    log_info "Run 'source $SHELL_RC' or start a new terminal to apply changes"
else
    log_warn "Could not determine shell rc file. Please add the following to your shell profile:"
    echo -e "\nexport KUBECONFIG=\"$KUBE_CONFIG\"\n"
fi

log_info "Kubeconfig setup complete!"
log_info "You can now use kubectl commands as $SUDO_USER"
log_info "Example: kubectl get nodes"
