from hammerspace.client import HammerspaceApiClient

# Initialize the client
client = HammerspaceApiClient(
    base_url="https://10.200.120.200:8443/mgmt/v1.2/rest",
    username="admin",
    password="1Hammerspace!",
    verify_ssl=False
)

# Get all network interfaces
interfaces = client.network_interfaces.get()

print("Hammerspace Nodes:")
print("=" * 80)

# Track nodes we've already seen
seen_nodes = set()

for interface in interfaces:
    node = interface.get('node', {})
    node_name = node.get('name', 'Unknown')
    
    # Skip if we've already processed this node
    if node_name in seen_nodes:
        continue
        
    node_type = node.get('productNodeType', 'UNKNOWN')
    
    # Only process ANVIL and DSX nodes
    if node_type in ['ANVIL', 'DSX']:
        seen_nodes.add(node_name)
        ip_address = node.get('mgmtIpAddress', {}).get('address', 'N/A')
        
        print(f"\nNode Name: {node_name}")
        print(f"Type: {node_type}")
        print(f"IP Address: {ip_address}")
        print(f"Hardware State: {node.get('hwComponentState', 'N/A')}")
        print(f"Node State: {node.get('nodeState', 'N/A')}")
        print("-" * 40)

print("\n" + "=" * 80)
print(f"Found {len(seen_nodes)} nodes (ANVIL/DSX)")
