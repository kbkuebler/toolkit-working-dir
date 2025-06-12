# Monitoring Stack Bootstrap

This project provides a streamlined way to deploy a monitoring stack across multiple Kubernetes clusters.

## Prerequisites

- Python 3.8+
- `curl`
- The script will automatically install `kubectl`, `k3s`, `jq`, and `k9s` when possible.
- If `yq` cannot be installed via a package manager, it will be downloaded from the official GitHub release.
- Python packages listed in `requirements.txt` will be installed automatically using `pip3` if needed.

## Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd <repository-name>
   ```

2. **Edit the configuration**
   Update `config/config.yaml` with the IP addresses of your clusters:
   ```yaml
   clusters:
     - 10.200.120.200
     - 10.200.120.202
   ```

3. **Run the bootstrap script**
   ```bash
   ./bootstrap.sh
   ```

   Alternatively, if you want to apply the Kubernetes manifests directly, run:
   ```bash
   kubectl apply -k kustomize
   ```

   This will:
   - Validate your environment
  - Install `kubectl` and k3s if a cluster is not already available
  - Install `jq` and `k9s` when possible, downloading `yq` from GitHub if a package manager isn't available
  - Install required Python packages from `requirements.txt`
   - Deploy the monitoring stack to all specified clusters

## Configuration

The main configuration file (`config/config.yaml`) supports the following options:

- `clusters`: List of clusters to monitor
  - `name`: Cluster identifier
  - `api_server`: API server URL
  - `namespace`: (Optional) Override default namespace
- `defaults`: Default settings for all clusters
  - `namespace`: Default namespace (default: monitoring)
  - `prometheus`: Prometheus configuration
  - `loki`: Loki configuration
  - `vector`: Vector configuration

## Architecture

The bootstrap process consists of these main components:

1. **bootstrap.sh**: Main entry point that handles:
   - Environment validation (curl, python3)
  - Automatic installation of k3s, jq, and k9s when possible; `yq` is downloaded from GitHub if necessary
  - Python dependencies from `requirements.txt` are installed using `pip3`
   - Configuration loading and processing
   - Node discovery via Hammerspace SDK
   - Template rendering and Kubernetes deployment

2. **Node Discovery**:
   - Automatically discovers Anvil and DSX nodes using the Hammerspace SDK
   - Falls back to static configuration if discovery fails
   - Can be disabled with `--no-discover` flag

3. **Configuration**:
   - `config/config.yaml`: Centralized configuration
   - Supports multiple clusters with dynamic node discovery
   - Global settings for Prometheus and other components

## Adding a New Cluster

1. Add a new IP address to the `clusters` section in `config/config.yaml`
   ```yaml
   clusters:
     - 10.x.x.x
   ```

2. Run the bootstrap script:
   ```bash
   # With automatic node discovery (recommended)
   ./bootstrap.sh
   
   # Or with static configuration only
   ./bootstrap.sh --no-discover
   
   # Preview configuration without applying
   ./bootstrap.sh --config-only
   ```

## Troubleshooting

- **Missing dependencies**:
  - `python3` (the script installs requirements from `requirements.txt`)
  - `curl`
  - The script installs `kubectl`, `jq`, and `k9s` when possible. `yq` will be downloaded from the official GitHub release if it cannot be installed via a package manager.

- **Kubernetes access**: 
  ```bash
  # Verify access
  kubectl cluster-info
  ```

- **Node Discovery Issues**:
  - Check Hammerspace API connectivity
  - Verify credentials in environment variables:
    ```bash
    export HS_USERNAME=admin
    export HS_PASSWORD=your_password
    ```
  - Use `--no-discover` to skip discovery

- **Configuration**:
  - Check YAML syntax in config files
  - Use `--config-only` to validate before applying

- **Dashboard**:
  - If seeing 127.0.0.1 in dashboard, set the server address:
    ```bash
    export SERVER_ADDRESS=10.200.120.228
    ```

## Development

### Project Structure

```
.
├── config/
│   └── config.yaml          # Main configuration
├── scripts/
│   └── discover_nodes.py   # Node discovery script
├── prometheus/
│   ├── configmap.yaml.j2   # Prometheus config template
│   └── ...
└── Hammerspace_SDK/        # Hammerspace Python SDK
```

### Testing Changes

1. Validate configuration:
   ```bash
   ./bootstrap.sh --config-only
   ```

2. Test node discovery:
   ```bash
   python3 scripts/discover_nodes.py --config config/config.yaml --output discovered.json
   ```

## License

[Your License Here]
