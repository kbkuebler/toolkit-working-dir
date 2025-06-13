from hammerspace.client import HammerspaceApiClient

# Initialize the client
client = HammerspaceApiClient(
    base_url="https://10.200.120.200:8443/mgmt/v1.2/rest",
    username="admin",
    password="1Hammerspace!",
    verify_ssl=False
)

def get_management_ips():
    """
    Returns a dictionary of node names to their management IP addresses
    for ANVIL and DSX nodes
    """
    interfaces = client.network_interfaces.get()
    node_ips = {}
    
    for interface in interfaces:
        node = interface.get('node', {})
        node_name = node.get('name')
        node_type = node.get('productNodeType')
        
        # Only process ANVIL and DSX nodes we haven't seen yet
        if node_type in ['ANVIL', 'DSX'] and node_name and node_name not in node_ips:
            ip_address = node.get('mgmtIpAddress', {}).get('address')
            if ip_address:
                node_ips[node_name] = ip_address
    
    return node_ips

# Get all management IPs
node_ips = get_management_ips()

# Print in Prometheus static_configs format
print("# Prometheus static_configs for Hammerspace nodes")
print("scrape_configs:")
print("  - job_name: 'hammerspace'")
print("    static_configs:")
print("      - targets: [" + ", ".join(f"'{ip}:9100'" for ip in node_ips.values()) + "]")

# Print detailed information
print("\n# Node Details:")
for node_name, ip in node_ips.items():
    print(f"{node_name}: {ip}")

print(f"\nFound {len(node_ips)} nodes (ANVIL/DSX)")