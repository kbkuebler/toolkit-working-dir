#!/bin/bash
# This script is used by Kustomize to generate the Prometheus configuration

set -euo pipefail

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

# Run the Python script to generate the Prometheus configuration
"${ROOT_DIR}/scripts/generate_prometheus_config.py" \
  --config "${ROOT_DIR}/config/config.yaml" \
  --output "${SCRIPT_DIR}/generated-prometheus.yml"

# Output the ConfigMap YAML
cat <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
data:
  prometheus.yml: |
$(cat "${SCRIPT_DIR}/generated-prometheus.yml" | sed 's/^/    /')
EOF
