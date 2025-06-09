#!/usr/bin/env python3
"""
Setup script for deploying the monitoring stack across multiple clusters.
"""
import os
import sys
import yaml
import argparse
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass
import subprocess
import json

@dataclass
class ClusterConfig:
    name: str
    api_server: str
    namespace: str
    prometheus: Dict[str, Any]
    loki: Dict[str, Any]
    vector: Dict[str, Any]

class SetupManager:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = self._load_config()
        self.clusters: List[ClusterConfig] = []
        
    def _load_config(self) -> Dict[str, Any]:
        """Load and validate the configuration file."""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                
            # Basic validation
            if 'clusters' not in config or not isinstance(config['clusters'], list):
                raise ValueError("Configuration must contain a 'clusters' list")
                
            return config
            
        except Exception as e:
            print(f"Error loading config file: {e}", file=sys.stderr)
            sys.exit(1)
    
    def setup_clusters(self):
        """Process each cluster configuration."""
        print(f"Setting up monitoring for {len(self.config['clusters'])} clusters")
        
        for cluster in self.config['clusters']:
            try:
                self._setup_cluster(cluster)
            except Exception as e:
                print(f"Error setting up cluster {cluster.get('name', 'unknown')}: {e}", file=sys.stderr)
    
    def _setup_cluster(self, cluster_config: Dict[str, Any]):
        """Setup monitoring for a single cluster."""
        # Merge with defaults
        defaults = self.config.get('defaults', {})
        namespace = cluster_config.get('namespace', defaults.get('namespace', 'monitoring'))
        
        print(f"\n=== Setting up cluster: {cluster_config['name']} ===")
        print(f"API Server: {cluster_config['api_server']}")
        print(f"Namespace: {namespace}")
        
        # Here we would:
        # 1. Generate kustomize patches based on config
        # 2. Apply the monitoring stack
        # 3. Configure Prometheus/Loki/Vector as needed
        
        # Example: Create namespace if it doesn't exist
        self._create_namespace(namespace)
        
        # TODO: Add more setup steps here
        
    def _create_namespace(self, name: str):
        """Create a namespace if it doesn't exist."""
        cmd = ["kubectl", "get", "namespace", name, "--output=name"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Creating namespace: {name}")
            cmd = ["kubectl", "create", "namespace", name]
            subprocess.run(cmd, check=True)
        else:
            print(f"Namespace {name} already exists")

def main():
    parser = argparse.ArgumentParser(description='Setup monitoring stack across multiple clusters')
    parser.add_argument('--config', default='config/config.yaml',
                       help='Path to configuration file (default: config/config.yaml)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.config):
        print(f"Error: Config file '{args.config}' not found", file=sys.stderr)
        sys.exit(1)
    
    manager = SetupManager(args.config)
    manager.setup_clusters()

if __name__ == '__main__':
    main()
