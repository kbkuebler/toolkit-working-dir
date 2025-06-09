import os
import socket
from datetime import datetime
from typing import Dict, Any

import nicegui
from nicegui import ui
from kubernetes import client, config
from kubernetes.client import CoreV1Api, AppsV1Api

# Get server address for access links (default to localhost for development)
# Set SERVER_ADDRESS environment variable to the lab server's IP/hostname when running in the lab
SERVER_ADDRESS = os.environ.get('SERVER_ADDRESS', 'localhost')

# Configure Kubernetes client
config.load_kube_config()
v1 = CoreV1Api()
apps_v1 = AppsV1Api()

# Define services to monitor
SERVICES = {
    'grafana': {'port': 32000, 'deployment': 'grafana', 'namespace': 'hammerspace'},
    'prometheus': {'port': 32001, 'deployment': 'prometheus', 'namespace': 'hammerspace'},
    'loki': {'port': 32002, 'deployment': 'loki', 'namespace': 'hammerspace'},
    'vector': {'port': 32003, 'deployment': 'vector', 'namespace': 'hammerspace'},
    'csi-nfs-node': {'port': None, 'deployment': 'csi-nfs-node', 'namespace': 'kube-system', 'type': 'daemonset'}
}

def get_service_status(service_name):
    """Get status of a single service."""
    service = SERVICES[service_name]
    is_daemonset = service.get('type') == 'daemonset'
    
    status = {
        'name': service_name,
        'port': service['port'],
        'status': 'Unknown',
        'replicas': 0,
        'available_replicas': 0,
        'type': 'DaemonSet' if is_daemonset else 'Deployment',
        'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    try:
        if is_daemonset:
            # Handle DaemonSet
            daemonset = apps_v1.read_namespaced_daemon_set(
                name=service['deployment'],
                namespace=service['namespace']
            )
            status['replicas'] = daemonset.status.desired_number_scheduled or 0
            status['available_replicas'] = daemonset.status.number_available or 0
            status['status'] = 'Running' if status['available_replicas'] > 0 else 'Not Available'
            
            # Get pod details for the CSI driver
            pods = v1.list_namespaced_pod(
                namespace=service['namespace'],
                label_selector="app.kubernetes.io/name=csi-nfs-node"
            )
            status['pods'] = [
                {
                    'name': pod.metadata.name,
                    'status': pod.status.phase,
                    'node': pod.spec.node_name,
                    'containers': [
                        {
                            'name': container.name,
                            'ready': container.ready,
                            'restart_count': container.restart_count
                        }
                        for container in pod.status.container_statuses or []
                    ]
                }
                for pod in pods.items
            ]
        else:
            # Handle regular deployments
            deployment = apps_v1.read_namespaced_deployment(
                name=service['deployment'],
                namespace=service['namespace']
            )
            status['replicas'] = deployment.status.replicas or 0
            status['available_replicas'] = deployment.status.available_replicas or 0
            status['status'] = 'Running' if status['available_replicas'] > 0 else 'Not Available'
            
    except Exception as e:
        status['error'] = str(e)
        status['status'] = 'Error'
    
    return status

def create_card_content(service_name, status):
    """Create the content of a service card."""
    is_csi = service_name == 'csi-nfs-node'
    
    with ui.column().classes('w-full'):
        # Header with service name and status
        with ui.row().classes('w-full justify-between items-center'):
            ui.label(service_name).classes('text-lg font-bold')
            ui.label(status['status']).classes(
                f'px-2 py-1 rounded text-white ' \
                f'{"bg-green-500" if status["status"] == "Running" else "bg-yellow-500" if status["status"] == "Not Available" else "bg-red-500"}'
            )
        # Add deployment type badge
        ui.badge(status['type'], color='blue').props('dense outline')
        
        ui.separator()
        
        with ui.column():
            # Show different info for CSI driver
            if is_csi:
                ui.label(f"Nodes: {status['available_replicas']}/{status['replicas']}")
                
            # Show port and access link if available
            if status['port']:
                with ui.row().classes('items-center'):
                    ui.label("Access:")
                    ui.link("Open", f"http://{SERVER_ADDRESS}:{status['port']}")
                    ui.link(" (Copy URL)", f"http://{SERVER_ADDRESS}:{status['port']}", 
                           new_tab=False).on("click", lambda e, url=f"http://{SERVER_ADDRESS}:{status['port']}": 
                                           ui.run_javascript(f'navigator.clipboard.writeText("{url}")'))
            
            # Show any errors
            if 'error' in status:
                ui.label(f"Error: {status['error']}").classes('text-red-500')
            
            # Last update time
            ui.label(f"Last checked: {status['last_update']}").classes('text-xs text-gray-500')

def create_card(service_name, status):
    """Create a card for a service."""
    card = ui.card().classes('w-96' if service_name == 'csi-nfs-node' else 'w-80')
    card.service_name = service_name  # Store service name for updates
    with card:
        create_card_content(service_name, status)
    return card

def update_all_cards():
    """Update all service cards with current status."""
    for service_name in SERVICES:
        status = get_service_status(service_name)
        # Find and update the card
        for card in ui.card:
            if hasattr(card, 'service_name') and card.service_name == service_name:
                # Clear and recreate the card with new status
                card.clear()
                with card:
                    create_card_content(service_name, status)
                break

def create_dashboard():
    """Create the dashboard UI."""
    ui.page_title("Hammerspace Showcase")
    
    # Create a header with a more visible refresh button
    with ui.header().classes('justify-between items-center bg-blue-600 text-white p-4'):
        ui.label('Hammerspace Showcase').classes('text-xl font-bold')
        ui.button('Refresh', on_click=update_all_cards, icon='refresh')\
            .classes('bg-white text-blue-600 hover:bg-blue-50 px-4 py-2 rounded')\
            .props('flat')
    
    # Create the main content area
    with ui.column().classes('w-full p-4'):
        with ui.row().classes('w-full flex-wrap gap-4') as cards_container:
            # Initial population of cards
            for service_name in SERVICES:
                status = get_service_status(service_name)
                create_card(service_name, status)

# Create and run the dashboard
if __name__ in {"__main__", "__mp_main__"}:
    create_dashboard()
    ui.run(port=8080, reload=True,host='0.0.0.0')
