#!/usr/bin/env python3
"""
Hammerspace Node Discovery Script

This script discovers Anvil and DSX nodes in a Hammerspace cluster and returns
node information in a structured JSON format suitable for Prometheus configuration.

Usage:
    python get_nodes.py --cluster-ip <cluster-ip> [--username <username>] [--password <password>]

Environment Variables:
    HS_USERNAME: Hammerspace username (default: admin)
    HS_PASSWORD: Hammerspace password (default: 1Hammerspace!)
"""

import os
import sys
import json
import argparse
from typing import Dict, List, Optional, TypedDict

from hammerspace.client import HammerspaceApiClient


class NodeInfo(TypedDict):
    """Type definition for node information."""
    name: str
    ip: str
    type: str  # 'anvil' or 'dsx'

    product_node_type: str  # Original product node type from API


def get_management_ips(
    client: HammerspaceApiClient,
    node_types: Optional[List[str]] = None
) -> List[NodeInfo]:
    """
    Get management IPs for nodes of specified types.

    Args:
        client: Initialized Hammerspace API client
        node_types: List of node types to include (e.g., ['ANVIL', 'DSX'])

    Returns:
        List of node information dictionaries
    """
    if node_types is None:
        node_types = ['ANVIL', 'DSX']
    
    node_types = [t.upper() for t in node_types]
    interfaces = client.network_interfaces.get()
    
    # Track nodes we've already seen
    seen_nodes = set()
    nodes = []
    
    for interface in interfaces:
        node = interface.get('node', {})
        node_name = node.get('name')
        node_type = node.get('productNodeType', '').upper()
        
        # Skip if not a node type we're interested in or already processed
        if (node_type not in node_types or 
            not node_name or 
            node_name in seen_nodes):
            continue
            
        ip_address = node.get('mgmtIpAddress', {}).get('address')
        if not ip_address:
            continue
            
        seen_nodes.add(node_name)
        
        # Normalize node type to lowercase for our config
        normalized_type = node_type.lower()
        if normalized_type == 'anvil':
            node_type_short = 'anvil'
        elif normalized_type == 'dsx':
            node_type_short = 'dsx'
        else:
            node_type_short = normalized_type
            
        nodes.append({
            'name': node_name,
            'ip': ip_address,
            'type': node_type_short,
            'product_node_type': node_type
        })
    
    return nodes


def main():
    """Main function to parse arguments and run the discovery."""
    parser = argparse.ArgumentParser(description='Discover Hammerspace nodes')
    parser.add_argument('--cluster-ip', required=True, help='Hammerspace cluster management IP')
    parser.add_argument('--username', default=os.getenv('HS_USERNAME', 'admin'),
                      help='Hammerspace username (default: admin)')
    parser.add_argument('--password', default=os.getenv('HS_PASSWORD', '1Hammerspace!'),
                      help='Hammerspace password')
    parser.add_argument('--output-format', choices=['json', 'prometheus'], default='json',
                      help='Output format (default: json)')
    
    args = parser.parse_args()
    
    try:
        # Initialize the client
        client = HammerspaceApiClient(
            base_url=f"https://{args.cluster_ip}:8443/mgmt/v1.2/rest",
            username=args.username,
            password=args.password,
            verify_ssl=False
        )
        
        # Get node information
        nodes = get_management_ips(client)
        
        if args.output_format == 'prometheus':
            # Output in Prometheus static_configs format
            print("# Prometheus static_configs for Hammerspace nodes")
            print("scrape_configs:")
            print("  - job_name: 'hammerspace'")
            print("    static_configs:")
            print("      - targets: [" + 
                  ", ".join(f"'{node['ip']}:9100'" for node in nodes) + "]")
            
            print("\n# Node Details:")
            for node in nodes:
                print(f"{node['name']} ({node['type']}): {node['ip']}")
            
            print(f"\nFound {len(nodes)} nodes")
        else:
            # Output as JSON for our config system
            print(json.dumps(nodes, indent=2))
            
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
