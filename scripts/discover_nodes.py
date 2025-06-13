#!/usr/bin/env python3
"""
Node Discovery Script for Hammerspace Clusters

This script discovers nodes in Hammerspace clusters and updates the configuration
with the discovered node information.
"""

import os
import sys
import argparse
import yaml
from typing import Dict, Any, List, Optional, Union
import logging
import requests
from urllib.parse import urljoin
from requests.auth import HTTPBasicAuth

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

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

def get_hs_credentials(config: dict) -> HTTPBasicAuth:
    """
    Get Hammerspace authentication credentials.
    
    Args:
        config: The configuration dictionary
        
    Returns:
        HTTPBasicAuth object if credentials are available, None otherwise
    """
    logger.debug("Looking for credentials in config and environment variables")
    
    # Get username and password from config or environment
    config_username = config.get("hammerspace", {}).get("username")
    env_username = os.environ.get("HS_USERNAME")
    username = config_username or env_username
    
    config_password = config.get("hammerspace", {}).get("password")
    env_password = os.environ.get("HS_PASSWORD")
    password = config_password or env_password
    
    logger.debug(f"Config username: {'[REDACTED]' if config_username else 'Not found'}")
    logger.debug(f"Env username: {'[REDACTED]' if env_username else 'Not found'}")
    logger.debug(f"Config password: {'[REDACTED]' if config_password else 'Not found'}")
    logger.debug(f"Env password: {'[REDACTED]' if env_password else 'Not found'}")
    
    if not username or not password:
        logger.warning("Hammerspace credentials not found in config or environment variables")
        return None
        
    logger.debug("Credentials found, creating HTTPBasicAuth")
    return HTTPBasicAuth(username, password)

def get_hs_api_url(config: Dict[str, Any]) -> Optional[str]:
    """
    Get the Hammerspace API URL.
    
    Args:
        config: The configuration dictionary
        
    Returns:
        The API URL if configured, None otherwise
    """
    # Check config file first, then environment variable
    return config.get('hammerspace', {}).get('api_url') or os.getenv('HS_API_URL')

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
        Get all nodes from the Hammerspace cluster by querying network interfaces.
        Filters for ANVIL and DSX nodes and extracts management IP addresses.
        
        Returns:
            List of node objects with management IP addresses
            
        Raises:
            requests.RequestException: If the API request fails
        """
        # Use the correct endpoint from the SDK
        url = urljoin(f"{self.base_url}/", "network-interfaces")
        try:
            logger.debug(f"Fetching network interfaces from: {url}")
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            # The response should be a list of interfaces
            interfaces = response.json()
            if not isinstance(interfaces, list):
                logger.error(f"Unexpected response format: {interfaces}")
                return []
            
            # Extract nodes with management IPs, filtering for ANVIL/DSX nodes
            nodes = []
            seen_nodes = set()
            
            for interface in interfaces:
                node = interface.get('node', {})
                node_name = node.get('name')
                node_type = node.get('productNodeType')
                
                # Only process ANVIL and DSX nodes we haven't seen yet
                if node_type in ['ANVIL', 'DSX'] and node_name and node_name not in seen_nodes:
                    ip_address = node.get('mgmtIpAddress', {}).get('address')
                    if ip_address:
                        seen_nodes.add(node_name)
                        nodes.append({
                            'name': node_name,
                            'type': node_type,
                            'ip_address': ip_address,
                            'node_data': node  # Include full node data for reference
                        })
            
            logger.info(f"Found {len(nodes)} ANVIL/DSX nodes with management IPs from {len(interfaces)} interfaces")
            return nodes
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch network interfaces: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                try:
                    logger.error(f"Response body: {e.response.text}")
                except Exception as parse_error:
                    logger.error(f"Could not parse response body: {parse_error}")
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
    
    logger.debug(f"Auth object: {'Present' if auth else 'None'}")
    logger.debug(f"API URL: {api_url}")
    
    if not auth or not api_url:
        logger.warning("Skipping node discovery: Missing credentials or API URL")
        if not auth:
            logger.warning("No authentication credentials found")
        if not api_url:
            logger.warning("No API URL found in config")
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
        existing_ips = {node.get('ip') for node in config.get('clusters', []) if node.get('ip')}
        
        # Initialize clusters list if it doesn't exist
        if 'clusters' not in config:
            config['clusters'] = []
        
        # Add discovered nodes that aren't already in the config
        for node in nodes:
            node_ip = node.get('ip_address')
            node_name = node.get('name')
            node_type = node.get('type')
            
            if not node_ip or not node_name:
                logger.warning(f"Skipping node with missing IP or name: {node}")
                continue
                
            if node_ip not in existing_ips:
                config['clusters'].append({
                    'name': node_name,
                    'ip': node_ip,
                    'type': node_type,
                    'discovered': True
                })
                existing_ips.add(node_ip)
                logger.info(f"Added discovered node: {node_name} ({node_type}) at {node_ip}")
            else:
                logger.debug(f"Node {node_name} ({node_ip}) already exists in config")
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

def generate_prometheus_config(nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate Prometheus scrape configuration from discovered nodes.
    
    Args:
        nodes: List of discovered nodes with IP addresses
        
    Returns:
        Dictionary containing Prometheus scrape configuration
    """
    # Filter nodes with IP addresses
    targets = [f"{node['ip']}:9100" for node in nodes if node.get('ip')]
    
    # Create Prometheus scrape config
    prometheus_config = {
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
            }
        ]
    }
    
    logger.info(f"Generated Prometheus config for {len(targets)} targets")
    return prometheus_config

def main():
    """Main entry point for the script."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Discover nodes in Hammerspace clusters')
    parser.add_argument('--config', required=True, help='Path to the configuration file')
    parser.add_argument('--output', required=True, help='Path to the output file')
    parser.add_argument('--username', help='Hammerspace API username (overrides config)')
    parser.add_argument('--password', help='Hammerspace API password (overrides config)')
    parser.add_argument('--api-url', help='Hammerspace API URL (overrides config)')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--prometheus-output', help='Path to output Prometheus configuration')
    args = parser.parse_args()

    # Configure logging level
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO,
                      format='%(levelname)s: %(message)s')
    
    try:
        # Load config
        config = load_config(args.config)
        
        # Override config with command line arguments
        if args.username:
            config.setdefault('hammerspace', {})['username'] = args.username
        if args.password:
            config.setdefault('hammerspace', {})['password'] = args.password
        if args.api_url:
            config.setdefault('hammerspace', {})['api_url'] = args.api_url
        
        # Discover nodes
        config = discover_nodes(config)
        
        # Save updated config
        with open(args.output, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        logger.info(f"✓ Configuration saved to {args.output}")
        
        # Generate and save Prometheus config if requested
        if args.prometheus_output:
            try:
                # Get all nodes with IPs
                nodes = [node for node in config.get('clusters', []) if node.get('ip')]
                if not nodes:
                    logger.warning("No nodes with IP addresses found for Prometheus configuration")
                else:
                    prometheus_config = generate_prometheus_config(nodes)
                    
                    # Ensure directory exists
                    os.makedirs(os.path.dirname(os.path.abspath(args.prometheus_output)), exist_ok=True)
                    
                    # Save Prometheus config
                    with open(args.prometheus_output, 'w') as f:
                        yaml.dump(prometheus_config, f, default_flow_style=False, sort_keys=False)
                    logger.info(f"✓ Prometheus configuration saved to {os.path.abspath(args.prometheus_output)}")
                    
                    # Print the generated config for verification
                    if args.debug:
                        logger.debug("Generated Prometheus configuration:")
                        with open(args.prometheus_output, 'r') as f:
                            logger.debug(f.read())
                            
            except Exception as e:
                logger.error(f"Failed to generate Prometheus configuration: {e}", exc_info=args.debug)
        
        return 0
        
    except ConfigError as e:
        logger.error(f"Configuration error: {e}")
        return 1
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=args.debug)
        return 1


if __name__ == '__main__':
    main()
