#!/usr/bin/env python3
"""
Node Discovery Script for Hammerspace Clusters (No SSL Verify)

This is a temporary version of the script with SSL verification disabled for testing.
"""

import os
import sys
import argparse
import yaml
import logging
import requests
from urllib.parse import urljoin
from requests.auth import HTTPBasicAuth

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Disable SSL warnings for testing
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class ConfigError(Exception):
    """Custom exception for configuration errors."""
    pass

def load_config(config_file: str) -> dict:
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
            config = yaml.safe_load(f) or {}
        return config
    except yaml.YAMLError as e:
        raise ConfigError(f"Error parsing YAML config: {str(e)}")
    except Exception as e:
        raise ConfigError(f"Error loading config file: {str(e)}")

def normalize_clusters(clusters: list) -> list:
    """Ensure each cluster entry is a dictionary with at least an IP address."""
    normalized = []
    for cluster in clusters:
        if isinstance(cluster, str):
            normalized.append({"ip": cluster})
        elif isinstance(cluster, dict) and "ip" in cluster:
            normalized.append(cluster)
    return normalized

def get_hs_credentials(config: dict) -> HTTPBasicAuth:
    """
    Get Hammerspace authentication credentials.
    
    Args:
        config: The configuration dictionary
        
    Returns:
        HTTPBasicAuth object if credentials are available, None otherwise
    """
    username = config.get("hammerspace", {}).get("username") or os.environ.get("HS_USERNAME")
    password = config.get("hammerspace", {}).get("password") or os.environ.get("HS_PASSWORD")
    
    if not username or not password:
        logger.warning("Hammerspace credentials not found in config or environment variables")
        return None
        
    return HTTPBasicAuth(username, password)

def get_hs_api_url(config: dict) -> str:
    """
    Get the Hammerspace API URL.
    
    Args:
        config: The configuration dictionary
        
    Returns:
        The API URL if configured, None otherwise
    """
    return config.get("hammerspace", {}).get("api_url") or os.environ.get("HS_API_URL")

class HammerspaceClient:
    """Client for interacting with the Hammerspace API."""
    
    def __init__(self, base_url: str, auth: HTTPBasicAuth, verify_ssl: bool = False, timeout: int = 30):
        """
        Initialize the Hammerspace client.
        
        Args:
            base_url: Base URL of the Hammerspace API
            auth: Authentication credentials
            verify_ssl: Whether to verify SSL certificates (default: False for testing)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.auth = auth
        self.session.verify = verify_ssl  # Disable SSL verification for testing
        self.timeout = timeout
    
    def get_network_interfaces(self) -> list:
        """
        Get all network interfaces from the Hammerspace cluster.
        
        Returns:
            List of network interface objects
            
        Raises:
            requests.RequestException: If the API request fails
        """
        url = f"{self.base_url}/network/interfaces"
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json() or []
        except requests.RequestException as e:
            logger.error(f"Failed to fetch network interfaces: {e}")
            raise
    
    def get_nodes(self) -> list:
        """
        Get all nodes from the Hammerspace cluster by examining network interfaces.
        
        Returns:
            List of node objects with their management IPs
            
        Raises:
            requests.RequestException: If the API request fails
        """
        interfaces = self.get_network_interfaces()
        seen_nodes = set()
        nodes = []
        
        for interface in interfaces:
            node = interface.get('node', {})
            node_name = node.get('name')
            node_type = node.get('productNodeType', '').upper()
            
            # Skip if no node name or already processed
            if not node_name or node_name in seen_nodes:
                continue
                
            ip_address = node.get('mgmtIpAddress', {}).get('address')
            if not ip_address:
                continue
                
            seen_nodes.add(node_name)
            
            nodes.append({
                'name': node_name,
                'managementIp': ip_address,
                'productNodeType': node_type,
                'status': node.get('status', {})
            })
            
        return nodes

def discover_nodes(config: dict) -> dict:
    """
    Discover nodes from Hammerspace clusters.
    
    Args:
        config: The configuration dictionary
        
    Returns:
        Updated configuration with discovered nodes
    """
    # Ensure we have a clusters list
    if "clusters" not in config:
        config["clusters"] = []
    
    # Get credentials and API URL
    auth = get_hs_credentials(config)
    api_url = get_hs_api_url(config)
    
    if not auth or not api_url:
        logger.warning("Skipping node discovery: Missing credentials or API URL")
        return config
    
    # Normalize cluster configurations
    clusters = normalize_clusters(config["clusters"])
    
    try:
        logger.info(f"Discovering nodes from {api_url}")
        client = HammerspaceClient(api_url, auth, verify_ssl=False)  # Disable SSL verification
        nodes = client.get_nodes()
        
        # Update the config with discovered nodes
        for node in nodes:
            node_ip = node.get("managementIp")
            node_name = node.get("name", "")
            node_type = node.get("productNodeType", "").lower()
            
            if node_ip and node_name:
                # Add node to clusters if not already present
                if not any(c.get("ip") == node_ip for c in clusters):
                    clusters.append({
                        "ip": node_ip,
                        "name": node_name,
                        "type": node_type,
                        "status": node.get("status", {})
                    })
                    logger.info(f"Discovered node: {node_name} ({node_ip}) - Type: {node_type}")
        
        # Update the config with the discovered nodes
        config["clusters"] = clusters
        logger.info(f"Updated configuration with {len(nodes)} discovered nodes")
        
    except Exception as e:
        logger.error(f"Error during node discovery: {e}", exc_info=True)
    
    return config

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Discover nodes from Hammerspace clusters (No SSL Verify)')
    parser.add_argument('--config', required=True, help='Path to config file')
    parser.add_argument('--output', required=True, help='Output file for processed config')
    parser.add_argument('--username', help='Hammerspace API username')
    parser.add_argument('--password', help='Hammerspace API password')
    parser.add_argument('--api-url', help='Hammerspace API URL')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()

    # Configure logging level
    if args.debug:
        logger.setLevel(logging.DEBUG)

    # Allow credentials and API URL from CLI to override environment
    if args.username:
        os.environ['HS_USERNAME'] = args.username
    if args.password:
        os.environ['HS_PASSWORD'] = args.password
    if args.api_url:
        os.environ['HS_API_URL'] = args.api_url
    
    try:
        # Load config
        config = load_config(args.config)
        
        # Ensure config has required structure
        if 'clusters' not in config:
            config['clusters'] = []
        
        # Update config with discovered nodes
        updated_config = discover_nodes(config)
        
        # Ensure we have the global section
        if 'global' not in updated_config:
            updated_config['global'] = config.get('global', {})
        
        # Save updated config as YAML so it can be consumed directly
        with open(args.output, 'w') as f:
            yaml.safe_dump(updated_config, f)
            
        print(f"✓ Configuration updated with discovered nodes")
        
    except yaml.YAMLError as e:
        print(f"Error parsing YAML config: {str(e)}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
