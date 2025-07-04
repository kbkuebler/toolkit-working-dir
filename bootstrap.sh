#!/bin/bash

# Exit on error
set -e

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root to install system dependencies and k3s"
    echo "Please run with sudo or as root"
    exit 1
fi

# Set default values
CONFIG_FILE="${PWD}/config/config.yaml"
TEMP_DIR="${PWD}/.tmp"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KUBECONFIG="/etc/rancher/k3s/k3s.yaml"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Add local bin to PATH if it exists
if [ -d "/usr/local/bin" ]; then
    export PATH="/usr/local/bin:${PATH}"
fi

# Ensure ~/.local/bin exists and is in PATH
LOCAL_BIN="$HOME/.local/bin"
mkdir -p "$LOCAL_BIN"
if ! echo "$PATH" | tr ':' '\n' | grep -qx "$LOCAL_BIN"; then
    export PATH="$LOCAL_BIN:$PATH"
fi

# Default values
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

# Function to run a script with error handling
run_script() {
    local script="$1"
    local script_path="${SCRIPT_DIR}/scripts/${script}"
    
    if [ ! -f "$script_path" ]; then
        log_error "Script not found: $script"
        return 1
    fi
    
    log_info "Running ${script}..."
    # Install required dependencies
    if ! install_dependencies; then
        log_error "Failed to install required dependencies"
        return 1
    fi

    # Install Python dependencies
    if ! install_python_requirements; then
        log_error "Failed to install Python dependencies"
        return 1
    fi
    
    chmod +x "$script_path"
    
    # Run the script with sudo -E to preserve environment
    if ! sudo -E "$script_path"; then
        log_error "Failed to run ${script}"
        return 1
    fi
}

# Install dependencies using dedicated scripts
install_dependencies() {
    log_info "Installing required dependencies..."
    
    # Install yq if not present
    if ! command_exists yq; then
        log_info "Installing yq..."
        if ! run_script "get_yq.sh"; then
            log_error "Failed to install yq. Please check the script and try again."
            return 1
        fi
    fi
    
    # Install kubectl if not present
    if ! command_exists kubectl; then
        log_info "Installing kubectl..."
        if ! run_script "get_kubectl.sh"; then
            log_error "Failed to install kubectl. Please check the script and try again."
            return 1
        fi
    fi
    
    # Install k9s if not present (optional)
    if ! command_exists k9s; then
        log_info "Installing k9s (optional)..."
        if ! run_script "get_k9s.sh"; then
            log_warn "k9s installation failed but it's optional. Continuing..."
        fi
    fi
    
    # Verify all required commands are available
    local missing_deps=()
    for cmd in yq kubectl; do
        if ! command_exists "$cmd"; then
            missing_deps+=("$cmd")
        fi
    done
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        log_error "Missing required dependencies: ${missing_deps[*]}"
        return 1
    fi
    
    return 0
}

# Install yq using GitHub release
install_yq() {
    local version="4.30.2"
    local os=$(uname | tr '[:upper:]' '[:lower:]')
    local arch=$(uname -m)
    case "$arch" in
        x86_64) arch="amd64" ;;
        aarch64|arm64) arch="arm64" ;;
    esac

    local url="https://github.com/mikefarah/yq/releases/download/${version}/yq_${os}_${arch}"

    if curl -sL "$url" -o /usr/local/bin/yq \
        && chmod +x /usr/local/bin/yq; then
        log_info "Installed yq ${version} from GitHub release"
        return 0
    fi

    # If /usr/local/bin isn't writable, attempt user-local install
    local dest_dir="$HOME/.local/bin"
    mkdir -p "$dest_dir"
    if curl -sL "$url" -o "$dest_dir/yq" \
        && chmod +x "$dest_dir/yq"; then
        log_info "Installed yq ${version} to $dest_dir/yq"
        export PATH="$dest_dir:$PATH"
        if ! echo "$PATH" | tr ':' '\n' | grep -qx "$dest_dir"; then
            log_warn "$dest_dir is not in your PATH. Add it to your shell profile: export PATH=\"$dest_dir:\$PATH\""
        fi
        return 0
    fi

    log_warn "Failed to install yq"
    return 1
}

# Install kubectl using package manager or official release
install_kubectl() {
    if command_exists kubectl; then
        return 0
    fi

    # Try to install via package manager first
    if install_dependency kubectl kubectl; then
        return 0
    fi

    # Fallback to official Kubernetes release
    local version="v1.29.4"
    local os=$(uname | tr '[:upper:]' '[:lower:]')
    local arch=$(uname -m)
    case "$arch" in
        x86_64) arch="amd64" ;;
        aarch64|arm64) arch="arm64" ;;
    esac

    local url="https://dl.k8s.io/release/${version}/bin/${os}/${arch}/kubectl"

    if curl -sL "$url" -o /usr/local/bin/kubectl \
        && chmod +x /usr/local/bin/kubectl; then
        log_info "Installed kubectl ${version} from official release"
        return 0
    fi

    local dest_dir="$HOME/.local/bin"
    mkdir -p "$dest_dir"
    if curl -sL "$url" -o "$dest_dir/kubectl" \
        && chmod +x "$dest_dir/kubectl"; then
        log_info "Installed kubectl ${version} to $dest_dir/kubectl"
        export PATH="$dest_dir:$PATH"
        if ! echo "$PATH" | tr ':' '\n' | grep -qx "$dest_dir"; then
            log_warn "$dest_dir is not in your PATH. Add it to your shell profile: export PATH=\"$dest_dir:\$PATH\""
        fi
        return 0
    fi

    log_warn "Failed to install kubectl"
    return 1
}

# Install Python dependencies from requirements.txt
install_python_requirements() {
    if [ ! -f "requirements.txt" ]; then
        log_warn "requirements.txt not found, skipping Python package installation"
        return 0
    fi

    if ! command_exists pip3; then
        log_info "Installing pip3..."
        if ! install_dependency pip3 python3-pip; then
            log_warn "Failed to install pip3"
            return 1
        fi
    fi

    log_info "Installing Python packages from requirements.txt..."
    if ! pip3 install -r requirements.txt >/dev/null 2>&1; then
        log_warn "Failed to install Python requirements"
        return 1
    fi

    return 0
}

# Install local toolkit scripts to ~/.local/bin
install_tool_scripts() {
    local dest_dir="$HOME/.local/bin"
    mkdir -p "$dest_dir"

    for script in "$SCRIPT_DIR"/scripts/*; do
        [ -f "$script" ] || continue
        case "$script" in
            */__pycache__*) continue ;;
        esac
        install -m 755 "$script" "$dest_dir/$(basename "$script")"
    done
}

# Check for required commands
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
install_yq || true
install_dependency jq jq || true
install_k9s || true
install_kubectl || true
install_python_requirements || true

# Verify yq and jq exist after attempted installation
for cmd in yq jq kubectl; do
    if ! command_exists "$cmd"; then
        log_error "Required command '$cmd' is not installed"
        exit 1
    fi
done

# Set file paths
PROMETHEUS_CONFIG="$TEMP_DIR/prometheus-config-generated.yaml"
FINAL_CONFIG="$TEMP_DIR/final_config.yaml"

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

    if ! python3 scripts/discover_nodes.py \
        --config "$CONFIG_FILE" \
        --output "$FINAL_CONFIG" >/dev/null; then
        log_warn "Failed to run node discovery. Using static configuration."
        cp "$CONFIG_FILE" "$FINAL_CONFIG"
    fi
}

# Function to generate Prometheus configuration
generate_prometheus_config() {
    log_info "Generating Prometheus configuration..."

    # Create output directory if it doesn't exist
    mkdir -p "$(dirname "$PROMETHEUS_CONFIG")"

    # Render the Prometheus config using Python
    if ! python3 <<PYTHON
import yaml
import sys
from jinja2 import Environment, FileSystemLoader

try:
    # Load config
    with open("$FINAL_CONFIG", "r") as f:
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
        **{"global": config.get('global', {})},
        clusters=config.get('clusters', []),
        namespace=config.get('global', {}).get('namespace', 'monitoring')
    )

    # Write to file
    with open("$PROMETHEUS_CONFIG", "w") as f:
        f.write(rendered)

except Exception as e:
    print(f"Error generating Prometheus configuration: {str(e)}", file=sys.stderr)
    sys.exit(1)
PYTHON
    then
        log_error "Failed to generate Prometheus configuration"
        exit 1
    fi

    log_info "Generated Prometheus config at $PROMETHEUS_CONFIG"
}

# Function to generate CSI secret
generate_csi_secret() {
    log_info "[DEBUG] Entering generate_csi_secret function"
    local secret_dir="kustomize/overlays/cluster1/csi-secret"
    local secret_file="${secret_dir}/generated-secret.yaml"
    
    log_info "[DEBUG] Starting CSI secret generation..."
    log_info "[DEBUG] Current working directory: $(pwd)"
    log_info "[DEBUG] Script directory: ${SCRIPT_DIR:-Not set}"
    log_info "[DEBUG] Secret directory: ${secret_dir}"
    log_info "[DEBUG] Secret file: ${secret_file}"
    log_info "[DEBUG] Python path: $(which python3)"
    log_info "[DEBUG] Script path: ${SCRIPT_DIR}/scripts/generate_csi_secret.py"
    
    # Ensure the directory exists
    log_info "Creating secret directory: ${secret_dir}"
    mkdir -p "${secret_dir}" || {
        log_error "Failed to create directory: ${secret_dir}"
        return 1
    }
    log_info "Directory contents: $(ls -la "${secret_dir}/.." | grep csi-secret || echo 'No csi-secret directory found')"
    
    # Create a temporary file for the secret
    local temp_secret_file="${TEMP_DIR}/csi-secret-temp.yaml"
    
    # Generate the secret to a temporary file first
    if ! python3 "${SCRIPT_DIR}/scripts/generate_csi_secret.py" \
        --config "${CONFIG_FILE}" \
        --output "${temp_secret_file}" \
        --namespace kube-system; then
        log_error "Failed to generate CSI secret"
        return 1
    fi
    
    # Only proceed if the temporary file was created successfully
    if [ ! -f "${temp_secret_file}" ]; then
        log_error "CSI secret was not generated"
        return 1
    fi
    
    # Copy the generated secret to the final location
    cp "${temp_secret_file}" "${secret_file}"
    log_debug "Generated CSI secret at ${secret_file}"
    
    # Create or update the kustomization.yaml in the secret directory
    cat > "${secret_dir}/kustomization.yaml" << EOF
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

# This file is auto-generated by the bootstrap script
# Do not edit manually - changes will be overwritten

resources:
  - generated-secret.yaml

generatorOptions:
  disableNameSuffixHash: true
  labels:
    app.kubernetes.io/name: hammerspace-csi
    app.kubernetes.io/component: storage
    app.kubernetes.io/part-of: hammerspace
EOF
    
    if [ "${CONFIG_ONLY}" = true ]; then
        log_info "Skipping CSI secret application (--config-only flag set)"
        log_info "Generated secret is available at: ${secret_file}"
        return 0
    fi
    
    log_success "CSI secret generated successfully!"
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
    
    # Generate CSI secret first
    if ! generate_csi_secret; then
        log_warn "Failed to generate CSI secret, but continuing with installation"
    fi
    
    # Apply kustomization using kubectl
    if [ -d "kustomize" ]; then
        log_info "Applying kustomize configuration..."
        if ! kubectl apply -k kustomize -n "$namespace"; then
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

    # Install required dependencies first
    if ! install_dependencies; then
        log_error "Failed to install required dependencies"
        exit 1
    fi

    # Copy toolkit scripts to user's local bin for convenience
    install_tool_scripts

    # Ensure k3s is installed and running
    if [ -x "scripts/setup_k3s.sh" ]; then
        log_info "Checking k3s installation..."
        if scripts/setup_k3s.sh; then
            # Set up kubeconfig if k3s is installed successfully
            if [ -x "scripts/setup_kubeconfig.sh" ]; then
                log_info "Setting up kubeconfig..."
                if ! scripts/setup_kubeconfig.sh; then
                    log_warn "Failed to set up kubeconfig"
                fi
            else
                log_warn "scripts/setup_kubeconfig.sh not found; skipping kubeconfig setup"
            fi
        else
            log_warn "k3s setup failed or is unavailable"
        fi
    else
        log_warn "scripts/setup_k3s.sh not found; skipping k3s setup"
    fi
    
    # Validate configuration
    if ! validate_config; then
        log_error "Configuration validation failed"
        exit 1
    fi

    # Prepare final configuration
    if [ "$DISCOVER_NODES" = true ]; then
        discover_nodes
    else
        cp "$CONFIG_FILE" "$FINAL_CONFIG"
    fi

    # Generate Prometheus configuration
    generate_prometheus_config
    
    # Show config if config-only mode
    if [ "$CONFIG_ONLY" = true ]; then
        log_info "Final configuration written to $FINAL_CONFIG"
        if [ -f "$FINAL_CONFIG" ]; then
            cat "$FINAL_CONFIG"
        fi
        echo
        log_info "Prometheus scrape config written to $PROMETHEUS_CONFIG"
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
    local namespace="$(yq e '.global.namespace // "monitoring"' "$FINAL_CONFIG")"
    install_monitoring_stack "$namespace"
    
    # Cleanup
    cleanup
    
    log_info "Bootstrap completed successfully!"
}

# Run main function
main "$@"
