from nicegui import ui
from kubernetes import client, config
import os
from dotenv import load_dotenv
import time
from datetime import datetime
from typing import Dict, Any, Optional

# Load environment variables
load_dotenv()

def init_kubernetes():
    """Initialize Kubernetes client with default context."""
    try:
        # Try to load in-cluster config first (if running in a pod)
        config.load_incluster_config()
        print("Using in-cluster config")
    except config.config_exception.ConfigException:
        try:
            # Load kubeconfig and explicitly use the default context
            contexts, active_context = config.list_kube_config_contexts()
            context_names = [ctx['name'] for ctx in contexts]
            
            # Find the default context
            default_context = next((ctx for ctx in contexts if ctx['name'] == 'default'), None)
            if not default_context:
                print("Warning: 'default' context not found, using current context")
                config.load_kube_config()
            else:
                print(f"Using context: {default_context['name']} (cluster: {default_context['context'].get('cluster', 'unknown')})")
                config.load_kube_config(context=default_context['name'])
                
        except Exception as e:
            raise Exception(f"Failed to load kubeconfig: {str(e)}")
    
    # Get the Kubernetes API clients
    v1 = client.CoreV1Api()
    apps_v1 = client.AppsV1Api()
    return v1, apps_v1

# Initialize Kubernetes client
v1, apps_v1 = init_kubernetes()

# Store UI elements for each service
service_ui_elements: Dict[str, Dict[str, Any]] = {}

# Define the service ports and their corresponding deployment names
SERVICES = {
    'grafana': {
        'port': 32000,
        'deployment': 'grafana',
        'namespace': 'hammerspace'
    },
    'prometheus': {
        'port': 32001,
        'deployment': 'prometheus',
        'namespace': 'hammerspace'
    },
    'loki': {
        'port': 32002,
        'deployment': 'loki',
        'namespace': 'hammerspace'
    },
    'vector': {
        'port': 32003,
        'deployment': 'vector',
        'namespace': 'hammerspace'
    },
    'csi-driver': {
        'port': None,  # No direct access
        'deployment': 'csi-driver',
        'namespace': 'hammerspace'
    }
}

def get_service_status(service_name: str) -> dict:
    """Get detailed status information about a service."""
    try:
        service = SERVICES[service_name]
        
        # Get deployment status
        try:
            deployment = apps_v1.read_namespaced_deployment(
                name=service['deployment'],
                namespace=service['namespace']
            )
        except client.exceptions.ApiException as e:
            if e.status == 404:
                return {
                    'status': 'Not Found',
                    'error': f"Deployment {service['deployment']} not found in namespace {service['namespace']}",
                    'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            raise
        
        # Get pod status
        try:
            pods = v1.list_namespaced_pod(
                namespace=service['namespace'],
                label_selector=f'app={service_name}'
            )
        except client.exceptions.ApiException as e:
            if e.status == 403:
                return {
                    'status': 'Forbidden',
                    'error': f"Permission denied accessing pods in namespace {service['namespace']}",
                    'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            raise
        
        # Count pod statuses
        pod_statuses = {
            'running': 0,
            'pending': 0,
            'failed': 0,
            'total': len(pods.items)
        }
        
        for pod in pods.items:
            if pod.status.phase == 'Running':
                pod_statuses['running'] += 1
            elif pod.status.phase == 'Pending':
                pod_statuses['pending'] += 1
            elif pod.status.phase == 'Failed':
                pod_statuses['failed'] += 1
        
        return {
            'status': 'Running' if deployment.status.available_replicas == deployment.spec.replicas else 'Degraded',
            'replicas': f"{deployment.status.available_replicas}/{deployment.spec.replicas}",
            'pod_status': pod_statuses,
            'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        return {
            'status': 'Error',
            'error': str(e),
            'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

def update_service_card(service_name: str, status_info: dict):
    """Update or create a card for a specific service."""
    try:
        if service_name not in service_ui_elements:
            # Create new UI elements if they don't exist
            with ui.column() as col:
                card = ui.card().classes('w-80 m-2')
                with card:
                    title = ui.label(f'{service_name.capitalize()}').classes('text-lg font-bold')
                    status_row = ui.row()
                    status_icon = ui.icon('circle').classes('text-grey')
                    status_text = ui.label('Status: Checking...')
                    status_row.tailwind.align_items('center').gap('2')
                    
                    replicas_label = ui.label('Replicas: Checking...')
                    pods_label = ui.label('Pods: Checking...')
                    error_label = ui.label('').classes('text-red')
                    
                    if SERVICES[service_name]['port']:
                        service_link = ui.link('Open', f'http://localhost:{SERVICES[service_name]["port"]}').classes('text-blue-500')
                    
                    last_updated = ui.label('Last checked: Just now').classes('text-grey text-sm')
                
                # Store references to the UI elements
                service_ui_elements[service_name] = {
                    'card': card,
                    'title': title,
                    'status_icon': status_icon,
                    'status_text': status_text,
                    'replicas_label': replicas_label,
                    'pods_label': pods_label,
                    'error_label': error_label,
                    'last_updated': last_updated,
                    'container': col
                }
        
        # Update the UI elements with new status
        ui_elements = service_ui_elements[service_name]
        
        # Update status
        status = status_info.get('status', 'Unknown')
        if status == 'Running':
            ui_elements['status_icon'].props('name=check_circle color=green')
            ui_elements['status_text'].set_text(f'Status: {status}')
            ui_elements['status_text'].classes(replace='text-green')
        elif status == 'Degraded':
            ui_elements['status_icon'].props('name=warning color=orange')
            ui_elements['status_text'].set_text(f'Status: {status}')
            ui_elements['status_text'].classes(replace='text-orange')
        else:
            ui_elements['status_icon'].props('name=error color=red')
            ui_elements['status_text'].set_text(f'Status: {status}')
            ui_elements['status_text'].classes(replace='text-red')
        
        # Update replicas
        ui_elements['replicas_label'].set_text(f'Replicas: {status_info.get("replicas", "N/A")}')
        
        # Update pod status
        if 'pod_status' in status_info:
            pod_status = status_info['pod_status']
            ui_elements['pods_label'].set_text(f'Pods: {pod_status.get("running", 0)} running, {pod_status.get("pending", 0)} pending, {pod_status.get("failed", 0)} failed')
        
        # Update error message
        if 'error' in status_info and status_info['error']:
            ui_elements['error_label'].set_text(f'Error: {status_info["error"]}')
        else:
            ui_elements['error_label'].set_text('')
        
        # Update last updated time
        last_update = status_info.get('last_update', 'Unknown')
        ui_elements['last_updated'].set_text(f'Last checked: {last_update}')
        
    except Exception as e:
        print(f"Error updating UI for {service_name}: {str(e)}")
        if service_name in service_ui_elements and 'error_label' in service_ui_elements[service_name]:
            service_ui_elements[service_name]['error_label'].set_text(f'UI Error: {str(e)}')

def update_status():
    """Update all service statuses."""
    for service_name in SERVICES:
        try:
            status_info = get_service_status(service_name)
            update_service_card(service_name, status_info)
        except Exception as e:
            print(f"Error updating {service_name}: {e}")

    # Schedule next update (in seconds)
    ui.timer(30.0, update_status)  # Update every 30 seconds

def create_dashboard():
    """Create the main dashboard UI."""
    print("Creating dashboard UI...")  # Debug log
    try:
        with ui.column().classes('w-full p-4') as main_column:
            print("Created main column")  # Debug log
            ui.label('Hammerspace Monitoring Dashboard').classes('text-2xl font-bold mb-6 text-center')
            
            # Add a status indicator
            status_label = ui.label('Initializing...').classes('text-lg mb-4')
            
            # Create a grid for service cards
            with ui.grid(columns=2).classes('w-full gap-4') as grid:
                print("Created grid")  # Debug log
                status_label.set_text('Loading services...')
                
                # Initial update
                def initial_update():
                    try:
                        print("Running initial update...")  # Debug log
                        update_status()
                        status_label.set_text('Dashboard ready')
                        print("Initial update completed")  # Debug log
                    except Exception as e:
                        status_label.set_text(f'Error: {str(e)}')
                        print(f"Error in initial update: {e}")  # Debug log
                
                # Run initial update after a short delay
                ui.timer(0.1, initial_update, once=True)
    except Exception as e:
        print(f"Error creating dashboard: {e}")  # Debug log
        raise

if __name__ in {"__main__", "__mp_main__"}:
    create_dashboard()
    ui.run(title='Hammerspace Monitoring', port=8087, reload=True, host='0.0.0.0', show=False)
