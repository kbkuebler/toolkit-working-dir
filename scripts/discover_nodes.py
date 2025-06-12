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
import yaml
from typing import Dict, Any, List, Optional, Union
import logging
import requests
from urllib.parse import urljoin
from requests.auth import HTTPBasicAuth

# Add the SDK directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Hammerspace_SDK', 'hammerspace-api'))

# Try to import the SDK
try:
    from get_nodes import get_management_ips, HammerspaceApiClient
except ImportError:
    print("Error: Could not import Hammerspace SDK. Make sure it's installed.")
    sys.exit(1)

class ConfigError(Exception):
    """Custom exception for configuration errors."""
    pass

def load_config(config_file: str) -> Dict[str, Any]:
    """
    Load and parse the configuration file.
    
    Args:
        config_file: Path to the YAML configuration file
        
    Returns:
        Parsed configuration dictionary
        
    Raises:
        ConfigError: If the config file cannot be loaded or parsed
    """
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
            
        # Validate required sections
        if 'hammerspace' not in config:
            config['hammerspace'] = {}
            
        if 'clusters' not in config:
            config['clusters'] = []
            
        return config
        
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML in config file: {e}")
    except Exception as e:
        raise ConfigError(f"Error loading config file: {e}")

def normalize_clusters(clusters: List[Union[str, Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Ensure each cluster entry is a dictionary with at least an IP address."""
    normalized = []
    for idx, c in enumerate(clusters):
        if isinstance(c, str):
            normalized.append({'ip': c})
        elif isinstance(c, dict):
            normalized.append(c)
    return normalized

def get_hs_credentials(config: Dict[str, Any]) -> Optional[HTTPBasicAuth]:
    """
    Get Hammerspace authentication credentials.
    
    Args:
        config: The configuration dictionary
        
    Returns:
        HTTPBasicAuth object if credentials are available, None otherwise
    """
    # Check environment variables first
    username = os.getenv('HS_USERNAME') or config.get('hammerspace', {}).get('username')
    password = os.getenv('HS_PASSWORD') or config.get('hammerspace', {}).get('password')
    
    if not username or not password:
        logger.warning("Hammerspace credentials not found in config or environment variables")
        return None
        
    return HTTPBasicAuth(username, password)

def get_hs_api_url(config: Dict[str, Any]) -> Optional[str]:
    """
    Get the Hammerspace API URL.
    
    Args:
        config: The configuration dictionary
        
    Returns:
        The API URL if configured, None otherwise
    """
    return os.getenv('HS_API_URL') or config.get('hammerspace', {}).get('api_url')

class HammerspaceClient:
    """Client for interacting with the Hammerspace API."""
    
    def __init__(self, base_url: str, auth: HTTPBasicAuth, verify_ssl: bool = True, timeout: int = 30):
        """
        Initialize the Hammerspace client.
        
        Args:
            base_url: Base URL of the Hammerspace API
            auth: Authentication credentials
            verify_ssl: Whether to verify SSL certificates
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.auth = auth
        self.session.verify = verify_ssl
        self.timeout = timeout
        
    def get_nodes(self) -> List[Dict[str, Any]]:
        """
        Get all nodes from the Hammerspace cluster.
        
        Returns:
            List of node objects
            
        Raises:
            requests.RequestException: If the API request fails
        """
        url = urljoin(f"{self.base_url}/", "api/v1/nodes")
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json().get('items', [])
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch nodes: {e}")
            raise

def discover_nodes(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Discover nodes from Hammerspace clusters.
    
    Args:
        config: The configuration dictionary
        
    Returns:
        Updated configuration with discovered nodes
    """
    # Make a copy to avoid modifying the original
    config = config.copy()
    config['clusters'] = normalize_clusters(config.get('clusters', []))
    
    # Get credentials and API URL
    auth = get_hs_credentials(config)
    api_url = get_hs_api_url(config)
    
    if not auth or not api_url:
        logger.warning("Skipping node discovery: Missing credentials or API URL")
        return config
    
    try:
        # Initialize client
        verify_ssl = config.get('hammerspace', {}).get('ssl_verify', True)
        timeout = config.get('hammerspace', {}).get('timeout', 30)
        client = HammerspaceClient(api_url, auth, verify_ssl, timeout)
        
        # Get nodes
        logger.info(f"Discovering nodes from {api_url}")
        nodes = client.get_nodes()
        
        if not nodes:
            logger.warning("No nodes discovered")
            return config
            
        logger.info(f"Discovered {len(nodes)} nodes")
        
        # Update config with discovered nodes
        existing_ips = {node['ip'] for node in config.get('clusters', []) if 'ip' in node}
        
        for node in nodes:
            node_ip = node.get('ip')
            if not node_ip or node_ip in existing_ips:
                continue
                
            config['clusters'].append({
                'name': node.get('name', f"node-{len(config['clusters']) + 1}"),
                'ip': node_ip,
                'description': f"Discovered node: {node.get('name', '')}".strip(),
                'labels': {
                    'discovered': 'true',
                    'status': node.get('status', 'unknown').lower()
                },
                'ports': {
                    'metrics': 9100,
                    'api': 9101,
                    'c_metrics': 9102,
                    'c_advisor': 9103
                }
            })
            existing_ips.add(node_ip)
            
        logger.info(f"Updated configuration with {len(nodes)} discovered nodes")
        
    except Exception as e:
        logger.error(f"Error during node discovery: {e}", exc_info=True)
    
    return config

def main():
    """Main entry point for the script."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Discover nodes from Hammerspace clusters')
    parser.add_argument('--config', required=True, help='Path to config file')
    parser.add_argument('--output', help='Output file (default: stdout)')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Get credentials from args or environment
    username = args.username or os.getenv('HS_USERNAME')
    password = args.password or os.getenv('HS_PASSWORD')
    
    if not username or not password:
        print("Error: Hammerspace username and password must be provided via --username/--password "
              "or HS_USERNAME/HS_PASSWORD environment variables", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Load config
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f) or {}
        
        # Ensure config has required structure
        if 'clusters' not in config:
            config['clusters'] = []
        
        # Update config with discovered nodes
        updated_config = discover_nodes(config)
        
        # Ensure we have the global section
        if 'global' not in updated_config:
            updated_config['global'] = config.get('global', {})
        
        # Save updated config as JSON for easier processing in the template
        with open(args.output, 'w') as f:
            json.dump(updated_config, f, indent=2)
            
        print(f"✓ Configuration updated with discovered nodes")
        
    except yaml.YAMLError as e:
        print(f"Error parsing YAML config: {str(e)}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
