#!/bin/bash
set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install k3s
install_k3s() {
    echo -e "${YELLOW}Installing k3s...${NC}"
    curl -sfL https://get.k3s.io | sh -s - --write-kubeconfig-mode 644
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to install k3s${NC}"
        return 1
    fi
    
    # Add k3s to PATH for current session
    export PATH="$PATH:/usr/local/bin"
    export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
    
    # Wait for k3s to be ready
    echo -e "${YELLOW}Waiting for k3s to be ready...${NC}"
    local max_retries=30
    local count=0
    
    until systemctl is-active --quiet k3s || [ $count -ge $max_retries ]; do
        echo -n "."
        sleep 5
        ((count++))
    done
    
    if [ $count -ge $max_retries ]; then
        echo -e "\n${RED}Timed out waiting for k3s to start${NC}"
        return 1
    fi
    
    # Verify k3s is responding
    if ! kubectl get nodes >/dev/null 2>&1; then
        echo -e "${RED}Failed to connect to k3s cluster${NC}"
        return 1
    fi
    
    echo -e "\n${GREEN}✓ k3s is installed and running${NC}"
    return 0
}

# Function to check if k3s is running
check_k3s_status() {
    if ! command_exists k3s; then
        return 1
    fi
    
    if ! systemctl is-active --quiet k3s; then
        return 1
    fi
    
    if ! kubectl get nodes >/dev/null 2>&1; then
        return 1
    fi
    
    return 0
}

# Main execution
main() {
    echo -e "${GREEN}Checking k3s status...${NC}"
    
    if check_k3s_status; then
        echo -e "${GREEN}✓ k3s is already running${NC}"
        exit 0
    fi
    
    if ! install_k3s; then
        echo -e "${RED}Failed to install or start k3s${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ k3s setup completed successfully${NC}"
    
    # Print kubeconfig location
    echo -e "\n${YELLOW}To use kubectl, run:${NC}"
    echo "export KUBECONFIG=/etc/rancher/k3s/k3s.yaml"
}

# Run main function
main "$@"
