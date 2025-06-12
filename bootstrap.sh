#!/bin/bash
set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
CONFIG_FILE="config/config.yaml"
TEMP_DIR=".tmp"
DISCOVER_NODES=true
CONFIG_ONLY=false
CLEANUP=false
SHOW_HELP=false
VERBOSE=false

# Print usage information
print_help() {
    echo -e "${BLUE}Hammerspace Monitoring Bootstrap${NC}\n"
    echo -e "${BLUE}Usage: $0 [OPTIONS]${NC}\n"
    echo "Options:"
    echo "  --config FILE       Path to config file (default: config/config.yaml)"
    echo "  --config-only       Only generate config, don't apply to cluster"
    echo "  --no-discover      Skip node discovery"
    echo "  --cleanup          Remove temporary files after completion"
    echo "  --verbose, -v      Enable verbose output"
    echo "  --help, -h         Show this help message"
    echo -e "\nEnvironment variables:"
    echo "  HS_USERNAME        Hammerspace API username"
    echo "  HS_PASSWORD        Hammerspace API password"
    echo "  HS_API_URL         Hammerspace API URL"
    echo -e "\nExamples:"
    echo "  $0 --config my-config.yaml"
    echo "  HS_USERNAME=user HS_PASSWORD=pass $0 --config-only"
    echo "  $0 --verbose --no-discover"
    exit 0
}

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

log_debug() {
    if [ "$VERBOSE" = true ]; then
        echo -e "${BLUE}[DEBUG]${NC} $1"
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        --config-only)
            CONFIG_ONLY=true
            shift
            ;;
        --no-discover)
            DISCOVER_NODES=false
            shift
            ;;
        --cleanup)
            CLEANUP=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            SHOW_HELP=true
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            print_help
            exit 1
            ;;
    esac
done

# Show help if requested
if [ "$SHOW_HELP" = true ]; then
    print_help
fi

# Create temp directory if it doesn't exist
mkdir -p "$TEMP_DIR"


# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Attempt to install a command using available package managers
install_dependency() {
    local cmd="$1"
    local pkg="${2:-$1}"

    if command_exists "$cmd"; then
        return 0
    fi

    log_info "Attempting to install $cmd..."

    if command_exists apt-get; then
        if ! apt-get update -y >/dev/null 2>&1 || ! apt-get install -y "$pkg" >/dev/null 2>&1; then
            log_warn "Failed to install $cmd via apt-get"
            return 1
        fi
        return 0
    elif command_exists yum; then
        if ! yum install -y "$pkg" >/dev/null 2>&1; then
            log_warn "Failed to install $cmd via yum"
            return 1
        fi
        return 0
    elif command_exists brew; then
        if ! brew install "$pkg" >/dev/null 2>&1; then
            log_warn "Failed to install $cmd via brew"
            return 1
        fi
        return 0
    fi

    log_warn "No supported package manager found to install $cmd"
    return 1
}

# Install k9s from package manager or GitHub release if possible
install_k9s() {
    if command_exists k9s; then
        return 0
    fi

    # Try using package manager first
    if install_dependency k9s k9s; then
        return 0
    fi

    # Fallback to GitHub release
    local version="v0.32.4"
    local os=$(uname | tr '[:upper:]' '[:lower:]')
    local arch=$(uname -m)
    case "$arch" in
        x86_64) arch="amd64" ;;
        aarch64|arm64) arch="arm64" ;;
    esac

    local tar="k9s_${version}_${os}_${arch}.tar.gz"

    if curl -sL "https://github.com/derailed/k9s/releases/download/${version}/${tar}" -o "$tar" \
        && tar -xzf "$tar" k9s >/dev/null 2>&1 \
        && mv k9s /usr/local/bin/ >/dev/null 2>&1 \
        && rm -f "$tar"; then
        log_info "Installed k9s ${version}"
        return 0
    fi

    log_warn "Failed to install k9s"
    return 1
}

# Check for required commands (kubectl is optional as it will be installed with k3s)
REQUIRED_COMMANDS=("curl" "python3")
MISSING_COMMANDS=()

for cmd in "${REQUIRED_COMMANDS[@]}"; do
    if ! command_exists "$cmd"; then
        MISSING_COMMANDS+=("$cmd")
    fi
done

if [ ${#MISSING_COMMANDS[@]} -gt 0 ]; then
    log_error "Missing required commands: ${MISSING_COMMANDS[*]}"
    exit 1
fi

# Attempt to install auxiliary tools
install_dependency yq yq || true
install_dependency jq jq || true
install_k9s || true

# Verify yq and jq exist after attempted installation
for cmd in yq jq; do
    if ! command_exists "$cmd"; then
        log_error "Required command '$cmd' is not installed"
        exit 1
    fi
done

# Set file paths
PROMETHEUS_CONFIG="$TEMP_DIR/prometheus-config-generated.yaml"

# Function to validate configuration
validate_config() {
    log_info "Validating configuration..."
    
    if [ ! -f "$CONFIG_FILE" ]; then
        log_error "Config file not found: $CONFIG_FILE"
        exit 1
    fi
    
    # Validate YAML syntax
    if ! yq e '.' "$CONFIG_FILE" > /dev/null 2>&1; then
        log_error "Invalid YAML in config file: $CONFIG_FILE"
        exit 1
    fi
    
    # Check for required fields
    local required_fields=("global.namespace" "clusters")
    for field in "${required_fields[@]}"; do
        if ! yq e ".$field" "$CONFIG_FILE" > /dev/null 2>&1; then
            log_error "Missing required field in config: $field"
            exit 1
        fi
    done
    
    log_info "Configuration is valid"
}

# Function to discover nodes using Hammerspace API
discover_nodes() {
    log_info "Discovering nodes from Hammerspace..."
    
    # Get credentials from environment or config
    local hs_username="${HS_USERNAME:-$(yq e '.hammerspace.username // ""' "$CONFIG_FILE")}"
    local hs_password="${HS_PASSWORD:-$(yq e '.hammerspace.password // ""' "$CONFIG_FILE")}"
    local hs_api_url="${HS_API_URL:-$(yq e '.hammerspace.api_url // ""' "$CONFIG_FILE")}"
    
    if [ -z "$hs_username" ] || [ -z "$hs_password" ] || [ -z "$hs_api_url" ]; then
        log_warn "Missing Hammerspace credentials or API URL. Skipping node discovery."
        return 1
    fi
    
    # Call the discover_nodes.py script
    if ! python3 scripts/discover_nodes.py \
        --config "$CONFIG_FILE" \
        --output "$TEMP_DIR/discovered_nodes.yaml"; then
        log_warn "Failed to discover nodes from Hammerspace"
        return 1
    fi
    
    # Merge discovered nodes with existing config
    if [ -f "$TEMP_DIR/discovered_nodes.yaml" ]; then
        log_info "Merging discovered nodes into configuration..."
        yq eval-all 'select(fileIndex == 0) * select(fileIndex == 1)' "$CONFIG_FILE" "$TEMP_DIR/discovered_nodes.yaml" > "$TEMP_DIR/merged_config.yaml"
        mv "$TEMP_DIR/merged_config.yaml" "$CONFIG_FILE"
        log_info "Configuration updated with discovered nodes"
    fi
}

# Function to generate Prometheus configuration
generate_prometheus_config() {
    log_info "Generating Prometheus configuration..."
    
    # Create output directory if it doesn't exist
    mkdir -p "$(dirname "$PROMETHEUS_CONFIG")"
    
    # Render the Prometheus config using Python
    if ! python3 -c "
import yaml
import sys
from jinja2 import Environment, FileSystemLoader

try:
    # Load config
    with open('$CONFIG_FILE', 'r') as f:
        config = yaml.safe_load(f) or {}
    
    # Set default values if not present
    config.setdefault('global', {})
    config['global'].setdefault('prometheus', {
        'scrape_interval': '15s',
        'evaluation_interval': '15s',
        'retention': '7d',
        'storage_size': '10Gi'
    })
    
    # Ensure clusters is a list with proper structure
    if 'clusters' not in config or not isinstance(config['clusters'], list):
        config['clusters'] = []
    
    # Convert cluster entries that are just IP strings into dictionaries
    normalized = []
    for idx, cluster in enumerate(config['clusters']):
        if isinstance(cluster, str):
            cluster = {'ip': cluster}
        if not isinstance(cluster, dict):
            continue
        normalized.append(cluster)

        # Set default ports if not specified
        if 'ports' not in cluster or not isinstance(cluster['ports'], dict):
            cluster['ports'] = {}

        ports = cluster['ports']
        ports.setdefault('metrics', 9100)
        ports.setdefault('api', 9101)
        ports.setdefault('c_metrics', 9102)
        ports.setdefault('c_advisor', 9103)

        # Ensure cluster has a name
        if 'name' not in cluster or not cluster['name']:
            cluster['name'] = f"cluster-{idx + 1}"

        # Ensure cluster has labels
        if 'labels' not in cluster or not isinstance(cluster['labels'], dict):
            cluster['labels'] = {}
    config['clusters'] = normalized
    
    # Set up Jinja2 environment
    env = Environment(loader=FileSystemLoader('.'), trim_blocks=True, lstrip_blocks=True)
    template = env.get_template('prometheus/configmap.yaml.j2')
    
    # Render template
    rendered = template.render(
        global_config=config.get('global', {}),
        clusters=config.get('clusters', []),
        namespace=config.get('global', {}).get('namespace', 'monitoring')
    )
    
    # Write to file
    with open('$PROMETHEUS_CONFIG', 'w') as f:
        f.write(rendered)
        
except Exception as e:
    print(f'Error generating Prometheus configuration: {str(e)}', file=sys.stderr)
    sys.exit(1)
"
    then
        log_error "Failed to generate Prometheus configuration"
        exit 1
    fi
    
    log_info "Generated Prometheus config at $PROMETHEUS_CONFIG"
}

# Function to install monitoring stack
install_monitoring_stack() {
    local namespace="${1:-monitoring}"
    
    log_info "Installing monitoring stack in namespace: $namespace"
    
    # Create namespace if it doesn't exist
    if ! kubectl get namespace "$namespace" >/dev/null 2>&1; then
        log_info "Creating namespace: $namespace"
        if ! kubectl create namespace "$namespace"; then
            log_error "Failed to create namespace $namespace"
            return 1
        fi
    fi
    
    # Check if kustomize is available
    if ! command_exists kustomize; then
        log_info "Installing kustomize..."
        if ! (curl -s "https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh" | bash); then
            log_warn "Failed to install kustomize. Skipping monitoring stack installation."
            return 1
        fi
        export PATH="$PATH:$(pwd)"
    fi
    
    # Apply kustomization
    if [ -d "kustomize" ]; then
        log_info "Applying kustomize configuration..."
        if ! (cd kustomize && kustomize build . | kubectl apply -f - -n "$namespace"); then
            log_warn "Failed to apply kustomize configuration"
            return 1
        fi
    else
        log_warn "kustomize directory not found, skipping monitoring stack installation"
        return 1
    fi
    
    # Apply Prometheus config
    if [ -f "$PROMETHEUS_CONFIG" ]; then
        log_info "Applying Prometheus configuration..."
        if ! kubectl apply -f "$PROMETHEUS_CONFIG" -n "$namespace"; then
            log_warn "Failed to apply Prometheus configuration"
            return 1
        fi
    fi
    
    log_info "Monitoring stack installed in namespace: $namespace"
    
    # Show access information
    echo -e "\n${GREEN}=== Access Information ===${NC}"
    echo -e "Grafana:     http://localhost:3000 (port-forward required)"
    echo -e "Prometheus:  http://localhost:9090 (port-forward required)"
    echo -e "\nTo access the dashboards, run:"
    echo -e "  kubectl port-forward -n $namespace svc/grafana 3000:80"
    echo -e "  kubectl port-forward -n $namespace svc/prometheus 9090:9090"
    echo -e "\n${GREEN}==========================${NC}"
}

# Function to clean up temporary files
cleanup() {
    if [ "$CLEANUP" = true ]; then
        log_info "Cleaning up temporary files..."
        rm -rf "$TEMP_DIR"
    else
        log_info "Temporary files kept in: $TEMP_DIR"
        log_info "Use '--cleanup' to remove them automatically"
    fi
}

# Main function
main() {
    log_info "Starting bootstrap process..."

    # Ensure k3s is installed and running
    if [ -x "scripts/setup_k3s.sh" ]; then
        log_info "Checking k3s installation..."
        if ! scripts/setup_k3s.sh >/dev/null 2>&1; then
            log_warn "k3s setup failed or is unavailable"
        fi
    else
        log_warn "scripts/setup_k3s.sh not found; skipping k3s setup"
    fi
    
    # Validate configuration
    validate_config
    
    # Discover nodes if enabled
    if [ "$DISCOVER_NODES" = true ]; then
        discover_nodes
    fi
    
    # Generate Prometheus configuration
    generate_prometheus_config
    
    # Show config if config-only mode
    if [ "$CONFIG_ONLY" = true ]; then
        log_info "Generated Configuration"
        if [ -f "$PROMETHEUS_CONFIG" ]; then
            cat "$PROMETHEUS_CONFIG"
        else
            log_warn "No configuration file found at $PROMETHEUS_CONFIG"
        fi
        log_info "============================"
        cleanup
        exit 0
    fi
    
    # Install monitoring stack
    local namespace="$(yq e '.global.namespace // "monitoring"' "$CONFIG_FILE")"
    install_monitoring_stack "$namespace"
    
    # Cleanup
    cleanup
    
    log_info "Bootstrap completed successfully!"
}

# Run main function
main "$@"
