#!/usr/bin/env python3
"""
Generate Prometheus configuration from discovered nodes and templates.
"""

import os
import sys
import yaml
import argparse
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def normalize_node(node: Any) -> Dict[str, Any]:
    """Normalize a node entry to a dictionary format."""
    if isinstance(node, dict):
        return node
    elif isinstance(node, str):
        return {'ip': node}
    elif node is None:
        return {}
    else:
        logger.warning(f"Unexpected node format: {node}, type: {type(node)}")
        return {}

def load_nodes_config(config_path: str) -> List[Dict[str, Any]]:
    """Load nodes configuration from the main config file."""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f) or {}
        
        # Get clusters and normalize each entry
        clusters = config.get('clusters', [])
        if not isinstance(clusters, list):
            logger.warning(f"Expected 'clusters' to be a list, got {type(clusters)}")
            return []
            
        return [normalize_node(node) for node in clusters if node]
        
    except Exception as e:
        logger.error(f"Failed to load config from {config_path}: {e}")
        return []

def generate_prometheus_config(nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate Prometheus configuration from discovered nodes."""
    # Filter nodes with IP addresses and format as targets
    targets = []
    for node in nodes:
        ip = node.get('ip')
        if not ip:
            logger.debug(f"Skipping node with missing IP: {node}")
            continue
            
        # Convert IP to string in case it's not already
        ip_str = str(ip).strip()
        if not ip_str:
            logger.debug(f"Skipping empty IP in node: {node}")
            continue
            
        # Add port 9100 for node_exporter
        target = f"{ip_str}:9100"
        if target not in targets:  # Avoid duplicates
            targets.append(target)
    
    logger.info(f"Generated {len(targets)} targets for Prometheus")
    
    # Create Prometheus scrape config
    return {
        'global': {
            'scrape_interval': '15s',
            'evaluation_interval': '15s',
            'scrape_timeout': '10s',
        },
        'scrape_configs': [
            {
                'job_name': 'hammerspace-nodes',
                'scrape_interval': '15s',
                'static_configs': [
                    {
                        'targets': targets,
                        'labels': {
                            'job': 'hammerspace',
                            'environment': 'production'
                        }
                    }
                ]
            },
            {
                'job_name': 'prometheus',
                'static_configs': [
                    {'targets': ['localhost:9090']}
                ]
            },
            {
                'job_name': 'node',
                'kubernetes_sd_configs': [{'role': 'node'}],
                'relabel_configs': [
                    {
                        'source_labels': ['__address__'],
                        'regex': '(.*):10250',
                        'replacement': '${1}:9100',
                        'target_label': '__address__',
                        'action': 'replace'
                    },
                    {
                        'action': 'labelmap',
                        'regex': '__meta_kubernetes_node_label_(.+)'
                    }
                ]
            }
        ]
    }

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Generate Prometheus configuration')
    parser.add_argument('--config', required=True, help='Path to the main config file')
    parser.add_argument('--output', required=True, help='Path to the output file')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    # Load nodes from config
    nodes = load_nodes_config(args.config)
    if not nodes:
        logger.warning("No nodes found in config")
    else:
        logger.info(f"Loaded {len(nodes)} nodes from config")
    
    # Generate Prometheus config
    prometheus_config = generate_prometheus_config(nodes)
    
    # Ensure output directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write config to file
    with open(output_path, 'w') as f:
        yaml.dump(prometheus_config, f, default_flow_style=False, sort_keys=False)
    
    logger.info(f"✓ Prometheus configuration saved to {output_path}")
    
    # Print the generated config if debug is enabled
    if args.debug:
        logger.debug("Generated Prometheus configuration:")
        with open(output_path, 'r') as f:
            logger.debug(f.read())

if __name__ == '__main__':
    main()
