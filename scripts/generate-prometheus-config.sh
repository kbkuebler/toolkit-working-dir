#!/bin/bash
# Script to generate Prometheus configuration before Kustomize build

set -euo pipefail

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Generate the Prometheus configuration
"${SCRIPT_DIR}/generate_prometheus_config.py" \
  --config "${ROOT_DIR}/config/config.yaml" \
  --output "${ROOT_DIR}/kustomize/base/prometheus-resources/generated-prometheus.yml"

echo "✓ Generated Prometheus configuration at ${ROOT_DIR}/kustomize/base/prometheus-resources/generated-prometheus.yml"
