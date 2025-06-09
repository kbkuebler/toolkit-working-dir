#!/bin/bash
set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Default values
CONFIG_FILE="config/config.yaml"
TEMP_DIR=".tmp"
DISCOVER_NODES=true
CONFIG_ONLY=false

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
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Create temp directory if it doesn't exist
mkdir -p "$TEMP_DIR"

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check for required commands
for cmd in yq jq kubectl python3; do
    if ! command_exists "$cmd"; then
        echo -e "${RED}Error: $cmd is required but not installed.${NC}"
        exit 1
    fi
done

echo "Starting bootstrap process..."

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}Error: Config file $CONFIG_FILE not found.${NC}"
    exit 1
fi

echo "Loading configuration from $CONFIG_FILE..."

# Convert YAML to JSON for easier processing
if ! yq eval -o=json "$CONFIG_FILE" > "$TEMP_DIR/input_config.json"; then
    echo -e "${RED}Error: Failed to parse config file.${NC}"
    exit 1
fi

# Discover nodes if enabled
if [ "$DISCOVER_NODES" = true ]; then
    echo "Discovering nodes using Hammerspace SDK..."
    
    # Check if the discovery script exists
    DISCOVER_SCRIPT="scripts/discover_nodes.py"
    if [ ! -f "$DISCOVER_SCRIPT" ]; then
        echo -e "${YELLOW}Warning: Discovery script not found at $DISCOVER_SCRIPT. Using static configuration.${NC}"
        cp "$TEMP_DIR/input_config.json" "$TEMP_DIR/config.json"
    else
        # Run the discovery script
        if ! python3 "$DISCOVER_SCRIPT" \
            --config "$TEMP_DIR/input_config.json" \
            --output "$TEMP_DIR/discovered_config.json"; then
            echo -e "${YELLOW}Warning: Node discovery failed. Using static configuration.${NC}"
            cp "$TEMP_DIR/input_config.json" "$TEMP_DIR/config.json"
        else
            cp "$TEMP_DIR/discovered_config.json" "$TEMP_DIR/config.json"
            echo -e "${GREEN}✓ Node discovery complete${NC}"
        fi
    fi
else
    echo "Skipping node discovery (--no-discover flag set)"
    cp "$TEMP_DIR/input_config.json" "$TEMP_DIR/config.json"
fi

echo -e "${GREEN}✓ Configuration loaded${NC}"

# Function to render template
render_template() {
    local template_file=$1
    local config_file=$2
    local output_file=$3
    
    # Create a Python script to render the template
    cat > "$TEMP_DIR/render_template.py" << 'EOL'
import os
import sys
import json
from jinja2 import Environment, FileSystemLoader, select_autoescape

def main():
    if len(sys.argv) != 4:
        print("Usage: python render_template.py <template_file> <config_file> <output_file>")
        sys.exit(1)
    
    template_file = sys.argv[1]
    config_file = sys.argv[2]
    output_file = sys.argv[3]
    
    # Load config
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    # Set up Jinja2 environment
    env = Environment(
        loader=FileSystemLoader(os.path.dirname(template_file) or '.'),
        autoescape=select_autoescape(),
        trim_blocks=True,
        lstrip_blocks=True
    )
    
    # Prepare context with proper structure
    context = {
        'global': config.get('global', {}),
        'clusters': config.get('clusters', {})
    }
    
    # Render template with the full context
    template = env.get_template(os.path.basename(template_file))
    output = template.render(**context)
    
    # Write output
    with open(output_file, 'w') as f:
        f.write(output)

if __name__ == "__main__":
    main()
EOL

    # Install Jinja2 if not available
    if ! python3 -c "import jinja2" 2>/dev/null; then
        echo "Installing Jinja2..."
        if ! python3 -m pip install --user jinja2; then
            echo -e "${RED}Error: Failed to install Jinja2. Please install it manually with 'pip install jinja2'.${NC}"
            exit 1
        fi
    fi
    
    # Render the template
    python3 "$TEMP_DIR/render_template.py" \
        "$template_file" \
        "$config_file" \
        "$output_file"
}

# Generate Prometheus configuration
generate_prometheus_config() {
    echo "Generating Prometheus configuration..."
    
    # Render the template
    TEMPLATE_FILE="prometheus/configmap.yaml.j2"
    OUTPUT_FILE="$TEMP_DIR/prometheus-config-generated.yaml"
    
    # Ensure template exists
    if [ ! -f "$TEMPLATE_FILE" ]; then
        echo -e "${RED}Template file $TEMPLATE_FILE not found.${NC}"
        exit 1
    fi
    
    render_template "$TEMPLATE_FILE" "$TEMP_DIR/config.json" "$OUTPUT_FILE"
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}Error: Failed to generate Prometheus configuration.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ Generated Prometheus config at $OUTPUT_FILE${NC}"
    
    # Show the generated config
    
    # Apply the generated config
    kubectl apply -f "$config_file" -n "$namespace"
    
    echo -e "${GREEN}✓ Configuration applied to namespace: $namespace${NC}"
    echo -e "${GREEN}✓ Applied ConfigMap: prometheus-config${NC}"
}

# Cleanup temporary files
cleanup() {
    echo -e "${YELLOW}Cleaning up temporary files...${NC}"
    rm -rf "$TEMP_DIR"
}

# Show generated configuration
show_config() {
    local config_file="$TEMP_DIR/prometheus-config-generated.yaml"
    
    if [ ! -f "$config_file" ]; then
        echo -e "${RED}No generated configuration found.${NC}"
        exit 1
    fi
    
    echo -e "\n${GREEN}=== Generated Configuration ===${NC}"
    cat "$config_file"
    echo -e "\n${GREEN}=============================${NC}"
    
    echo -e "\n${YELLOW}Configuration saved to: $config_file${NC}"
    echo -e "${YELLOW}To apply this configuration, run:${NC}"
    echo -e "  kubectl apply -f $config_file -n $(yq e '.global.namespace // "monitoring"' "$CONFIG_FILE")"
}

# Main execution
main() {
    echo -e "${GREEN}Starting bootstrap process...${NC}"
    
    # Check for required tools
    check_yq
    
    # Validate config file exists
    if [ ! -f "$CONFIG_FILE" ]; then
        echo -e "${RED}Config file $CONFIG_FILE not found.${NC}"
        exit 1
    fi
    
    # Load configuration
    load_config
    
    # Setup Python environment
    check_python_requirements
    
    # Generate Prometheus configuration
    generate_prometheus_config
    
    if [ "$CONFIG_ONLY" = true ]; then
        echo -e "${GREEN}✓ Configuration generation complete.${NC}"
        show_config
    else
        # Validate Kubernetes access
        validate_kubeconfig
        
        # Apply the configuration
        apply_configuration
        
        # Cleanup
        cleanup
        
        echo -e "${GREEN}✓ Bootstrap process completed successfully!${NC}"
    fi
}

main "$@"
