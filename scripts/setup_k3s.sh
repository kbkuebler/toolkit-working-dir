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

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install k3s
install_k3s() {
    log_info "Starting k3s installation..."
    
    # Check if k3s is already installed
    if command_exists k3s && systemctl is-active --quiet k3s 2>/dev/null; then
        log_info "k3s is already installed and running"
        return 0
    fi
    
    # Install k3s with explicit flags
    log_info "Running k3s installer..."
    if ! curl -sfL https://get.k3s.io | INSTALL_K3S_SKIP_ENABLE=true sh -s - --write-kubeconfig-mode 644; then
        log_error "Failed to install k3s"
    fi
    
    # Enable and start k3s service
    log_info "Enabling k3s service..."
    if ! systemctl enable --now k3s 2>/dev/null; then
        log_error "Failed to enable k3s service"
    fi
    
    # Add k3s to PATH for current session
    export PATH="${PATH}:/usr/local/bin"
    export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
    
    # Wait for k3s to be ready with detailed status
    log_info "Waiting for k3s to become ready..."
    local max_retries=30
    local retry_delay=5
    local attempt=0
    
    while [ $attempt -lt $max_retries ]; do
        if systemctl is-active --quiet k3s; then
            # Check if k3s is reporting as ready in logs
            if journalctl -u k3s --no-pager -n 20 | grep -q 'k3s is up and running'; then
                # Verify API server is responding
                if kubectl get --raw /healthz &>/dev/null; then
                    # Final verification - check if nodes are reporting
                    if kubectl get nodes --no-headers 2>/dev/null | grep -q ' Ready '; then
                        log_info "k3s is now running and healthy"
                        return 0
                    fi
                fi
            fi
        fi
        
        # Show progress
        if [ $((attempt % 5)) -eq 0 ]; then
            log_info "Waiting for k3s to be ready (attempt $((attempt+1))/$max_retries)..."
            # Show recent logs for debugging
            journalctl -u k3s --no-pager -n 5 2>/dev/null | grep -i -E 'error|fail|warn|k3s' || true
        else
            echo -n "."
        fi
        
        sleep $retry_delay
        ((attempt++))
    done
    
    # If we get here, k3s didn't start properly
    log_warn "k3s failed to start properly. Check logs with: journalctl -u k3s"
    return 1
}

# Function to check if k3s is running and healthy
check_k3s_status() {
    local max_retries=10
    local retry_delay=5
    local attempt=0
    
    log_info "Checking k3s status..."
    
    # Check if k3s binary exists
    if ! command_exists k3s; then
        log_warn "k3s command not found"
        return 1
    fi
    
    # Check if k3s service is active
    if ! systemctl is-active --quiet k3s 2>/dev/null; then
        log_warn "k3s service is not running"
        return 1
    fi
    
    # Wait for k3s to be ready with retries
    while [ $attempt -lt $max_retries ]; do
        # Check if kubelet is healthy
        if ! journalctl -u k3s --no-pager -n 10 | grep -q 'k3s is up and running'; then
            log_info "Waiting for k3s to be ready (attempt $((attempt+1))/$max_retries)..."
            sleep $retry_delay
            ((attempt++))
            continue
        fi
        
        # Check if kubeconfig exists and is accessible
        local kubeconfig="/etc/rancher/k3s/k3s.yaml"
        if [ ! -f "$kubeconfig" ]; then
            log_info "Waiting for kubeconfig to be created..."
            sleep $retry_delay
            ((attempt++))
            continue
        fi
        
        # Check if we can query the API server
        if KUBECONFIG="$kubeconfig" kubectl get --raw /healthz &>/dev/null; then
            # Final verification - check if nodes are reporting
            if KUBECONFIG="$kubeconfig" kubectl get nodes --no-headers 2>/dev/null | grep -q ' Ready '; then
                log_info "k3s is running and healthy"
                return 0
            fi
        fi
        
        log_info "Waiting for k3s API to be ready..."
        sleep $retry_delay
        ((attempt++))
    done
    
    log_warn "k3s is not fully operational"
    return 1
}

# Main execution
main() {
    log_info "Checking k3s status..."
    
    if check_k3s_status; then
        log_info "✓ k3s is already running"
        exit 0
    fi
    
    if ! install_k3s; then
        log_error "Failed to install or start k3s"
    fi
    
    log_info "✓ k3s setup completed successfully"
    
    # Print kubeconfig location
    echo -e "\n${YELLOW}To use kubectl, run:${NC}"
    echo "export KUBECONFIG=/etc/rancher/k3s/k3s.yaml"
}

# Run main function
main "$@"
