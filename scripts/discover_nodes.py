#!/usr/bin/env python3
"""
Node Discovery Script for Hammerspace Clusters

This script discovers nodes in Hammerspace clusters and updates the configuration
with the discovered node information.
"""

import os
import sys
import json
import argparse
from typing import Dict, Any, List, Optional

# Add the SDK directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Hammerspace_SDK', 'hammerspace-api'))

# Try to import the SDK
try:
    from get_nodes import get_management_ips, HammerspaceApiClient
except ImportError:
    print("Error: Could not import Hammerspace SDK. Make sure it's installed.")
    sys.exit(1)


def discover_cluster_nodes(cluster_ip: str, username: str, password: str) -> List[Dict[str, Any]]:
    """
    Discover nodes in a Hammerspace cluster.
    
    Args:
        cluster_ip: IP address of the Hammerspace cluster
        username: Username for authentication
        password: Password for authentication
        
    Returns:
        List of node information dictionaries
    """
    try:
        client = HammerspaceApiClient(
            base_url=f"https://{cluster_ip}:8443/mgmt/v1.2/rest",
            username=username,
            password=password,
            verify_ssl=False
        )
        
        nodes = get_management_ips(client)
        
        # Convert to our config format
        config_nodes = []
        for node in nodes:
            config_nodes.append({
                'type': node['type'],  # 'anvil' or 'dsx'
                'ip': node['ip'],
                'name': node['name']
            })
            
        return config_nodes
        
    except Exception as e:
        print(f"Error discovering nodes for cluster {cluster_ip}: {str(e)}", file=sys.stderr)
        return []


def update_config_with_nodes(config: Dict[str, Any], username: str, password: str) -> Dict[str, Any]:
    """
    Update the configuration with discovered nodes.
    
    Args:
        config: The current configuration
        username: Hammerspace username
        password: Hammerspace password
        
    Returns:
        Updated configuration with discovered nodes
    """
    if 'clusters' not in config:
        return config
        
    updated_config = config.copy()
    
    for cluster_name, cluster in config['clusters'].items():
        if 'cluster_ip' not in cluster:
            print(f"Warning: No cluster_ip found for cluster {cluster_name}", file=sys.stderr)
            continue
            
        print(f"Discovering nodes for cluster {cluster_name} ({cluster['cluster_ip']})...")
        nodes = discover_cluster_nodes(
            cluster_ip=cluster['cluster_ip'],
            username=username,
            password=password
        )
        
        if nodes:
            if 'nodes' not in updated_config['clusters'][cluster_name]:
                updated_config['clusters'][cluster_name]['nodes'] = []
                
            # Update nodes in config
            updated_config['clusters'][cluster_name]['nodes'] = nodes
            print(f"Discovered {len(nodes)} nodes for cluster {cluster_name}")
        else:
            print(f"Warning: No nodes discovered for cluster {cluster_name}", file=sys.stderr)
    
    return updated_config


def main():
    """Main function to run the discovery."""
    parser = argparse.ArgumentParser(description='Discover Hammerspace nodes and update config')
    parser.add_argument('--config', required=True, help='Path to input config file')
    parser.add_argument('--output', required=True, help='Path to save updated config')
    parser.add_argument('--username', default=os.getenv('HS_USERNAME', 'admin'),
                      help='Hammerspace username (default: admin)')
    parser.add_argument('--password', default=os.getenv('HS_PASSWORD', '1Hammerspace!'),
                      help='Hammerspace password')
    
    args = parser.parse_args()
    
    try:
        # Load the config
        with open(args.config, 'r') as f:
            config = json.load(f)
            
        # Update config with discovered nodes
        updated_config = update_config_with_nodes(
            config=config,
            username=args.username,
            password=args.password
        )
        
        # Save the updated config
        with open(args.output, 'w') as f:
            json.dump(updated_config, f, indent=2)
            
        print(f"Configuration updated with discovered nodes and saved to {args.output}")
        
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
