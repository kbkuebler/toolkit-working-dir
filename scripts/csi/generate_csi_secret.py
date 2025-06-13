#!/usr/bin/env python3
"""
Generate Kubernetes Secret for Hammerspace CSI driver credentials.

This script reads the Hammerspace API credentials and endpoint from config.yaml,
base64 encodes the username and password, and generates a Kubernetes Secret YAML.
"""

import argparse
import base64
import os
import sys
import yaml
from pathlib import Path

def load_config(config_path):
    """Load and parse the config.yaml file."""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: Config file not found at {config_path}", file=sys.stderr)
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML in config file: {e}", file=sys.stderr)
        sys.exit(1)

def generate_secret_yaml(username, password, endpoint, namespace="kube-system"):
    """Generate Kubernetes Secret YAML with base64 encoded credentials."""
    # Encode username and password as base64
    username_b64 = base64.b64encode(username.encode('utf-8')).decode('utf-8')
    password_b64 = base64.b64encode(password.encode('utf-8')).decode('utf-8')
    
    # Create the Secret YAML
    secret = {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {
            "name": "com.hammerspace.csi.credentials",
            "namespace": namespace
        },
        "type": "Opaque",
        "data": {
            "username": username_b64,
            "password": password_b64
        },
        "stringData": {
            "endpoint": endpoint
        }
    }
    
    return yaml.dump(secret, default_flow_style=False)

def main():
    parser = argparse.ArgumentParser(description='Generate Kubernetes Secret for Hammerspace CSI driver')
    parser.add_argument('--config', default='../config/config.yaml',
                        help='Path to config.yaml (default: ../config/config.yaml)')
    parser.add_argument('--output', help='Output file path (default: print to stdout)')
    parser.add_argument('--namespace', default='kube-system',
                        help='Kubernetes namespace for the Secret (default: kube-system)')
    
    args = parser.parse_args()
    
    # Make config path absolute if it's relative
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = Path(__file__).parent.parent / config_path
    
    # Load config
    config = load_config(config_path)
    
    # Get credentials from config or environment variables
    hammerspace_config = config.get('hammerspace', {})
    username = hammerspace_config.get('username') or os.environ.get('HS_USERNAME')
    password = hammerspace_config.get('password') or os.environ.get('HS_PASSWORD')
    endpoint = hammerspace_config.get('api_url', '').rstrip('/').replace('/mgmt/v1.2/rest', '')
    
    # Validate required fields
    if not all([username, password, endpoint]):
        print("Error: Missing required configuration. Please ensure config.yaml contains hammerspace.username, "
              "hammerspace.password, and hammerspace.api_url, or set HS_USERNAME/HS_PASSWORD environment variables.",
              file=sys.stderr)
        sys.exit(1)
    
    # Generate the Secret YAML
    secret_yaml = generate_secret_yaml(username, password, endpoint, args.namespace)
    
    # Output to file or stdout
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(secret_yaml)
        print(f"✓ Generated CSI Secret at {output_path}")
    else:
        print(secret_yaml)

if __name__ == "__main__":
    main()
