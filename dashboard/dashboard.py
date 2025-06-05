from nicegui import ui
from kubernetes import client, config
import os
from dotenv import load_dotenv
import time
from datetime import datetime
import threading
from kubernetes.stream import stream
import paramiko
from io import StringIO

# Load environment variables
load_dotenv()

# Initialize Kubernetes client
try:
    # Try to load in-cluster config first
    config.load_incluster_config()
except:
    # Fall back to local kubeconfig
    config.load_kube_config()

# Get the Kubernetes API clients
v1 = client.CoreV1Api()
apps_v1 = client.AppsV1Api()

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
        'port': None,
        'deployment': 'csi-driver',
        'namespace': 'hammerspace'
    }
}

def get_service_status(service_name: str) -> dict:
    """Get detailed status information about a service."""
    try:
        service = SERVICES[service_name]
        
        # Get deployment status
        deployment = apps_v1.read_namespaced_deployment(
            name=service['deployment'],
            namespace=service['namespace']
        )
        
        # Get pod status
        pods = v1.list_namespaced_pod(
            namespace=service['namespace'],
            label_selector=f'app={service_name}'
        )
        
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
            'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'pods': pods.items
        }
    except Exception as e:
        return {
            'status': 'Error',
            'error': str(e),
            'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

def create_service_card(service_name: str, status_info: dict):
    """Create a card for a specific service."""
    with ui.card():
        ui.label(f'{service_name.capitalize()}')
        
        # Status indicator
        with ui.row():
            if status_info['status'] == 'Running':
                ui.icon('check_circle', color='green')
            elif status_info['status'] == 'Degraded':
                ui.icon('warning', color='orange')
            else:
                ui.icon('error', color='red')
            ui.label(f'Status: {status_info["status"]}')
        
        # Replicas
        ui.label(f'Replicas: {status_info.get("replicas", "N/A")}')
        
        # Pod status
        if 'pod_status' in status_info:
            pod_status = status_info['pod_status']
            ui.label(f'Pods: {pod_status["running"]} running, {pod_status["pending"]} pending, {pod_status["failed"]} failed')
        
        # Error message if present
        if 'error' in status_info:
            ui.label(f'Error: {status_info["error"]}').classes('text-red-500')
        
        # Link to service if available
        if SERVICES[service_name]['port']:
            ui.link('Open', f'http://localhost:{SERVICES[service_name]["port"]}')
        
        # Last update time
        ui.label(f'Last checked: {status_info["last_update"]}').classes('text-gray-500')
        
        # Pod details button
        if 'pods' in status_info:
            with ui.expansion('Pod Details', icon='expand_more'):
                for pod in status_info['pods']:
                    with ui.card():
                        ui.label(f'Pod: {pod.metadata.name}')
                        ui.label(f'Status: {pod.status.phase}')
                        ui.button('View Logs', on_click=lambda p=pod: view_pod_logs(p))
                        if pod.status.phase == 'Running':
                            ui.button('SSH', on_click=lambda p=pod: open_ssh_terminal(p))

def view_pod_logs(pod):
    """View pod logs in a new window."""
    with ui.dialog() as dialog, ui.card():
        ui.label(f'Logs for pod: {pod.metadata.name}')
        with ui.row():
            ui.button('Refresh', on_click=lambda: update_logs(pod, log_text))
            ui.button('Clear', on_click=lambda: log_text.set_text(''))
        log_text = ui.text_area(value='', rows=20, readonly=True)
        
        def update_logs():
            try:
                logs = v1.read_namespaced_pod_log(
                    name=pod.metadata.name,
                    namespace=pod.metadata.namespace,
                    tail_lines=100
                )
                log_text.set_text(logs)
            except Exception as e:
                log_text.set_text(f'Error fetching logs: {str(e)}')
        
        update_logs()  # Initial log fetch
    dialog.open()

def open_ssh_terminal(pod):
    """Open SSH terminal to pod."""
    with ui.dialog() as dialog, ui.card():
        ui.label(f'SSH Terminal to pod: {pod.metadata.name}')
        
        # Create terminal UI
        with ui.row():
            terminal = ui.text_area(value='', rows=20, readonly=True)
            
            def handle_input(e):
                if e.key == 'Enter':
                    command = e.value.strip()
                    try:
                        # Execute command using kubectl exec
                        resp = stream(
                            v1.connect_get_namespaced_pod_exec,
                            pod.metadata.name,
                            pod.metadata.namespace,
                            command=['sh', '-c', command],
                            stderr=True, stdin=True,
                            stdout=True, tty=True,
                            _preload_content=False
                        )
                        
                        # Read output
                        stdout = resp.read_stdout()
                        stderr = resp.read_stderr()
                        
                        # Update terminal
                        terminal.value += f'\n{command}\n'
                        if stdout:
                            terminal.value += stdout
                        if stderr:
                            terminal.value += stderr
                        terminal.scroll_to_bottom()
                        
                        # Clean up
                        resp.close()
                    except Exception as e:
                        terminal.value += f'\nError: {str(e)}\n'
                    
                    e.target.value = ''
            
            ui.input(placeholder='Enter command', on_key=handle_input)
            
        # Add a note about limitations
        ui.label('Note: This is a simplified terminal. Some interactive commands may not work.')
    dialog.open()

def update_status():
    """Update all service statuses."""
    for service_name in SERVICES:
        status_info = get_service_status(service_name)
        create_service_card(service_name, status_info)
    ui.timer(30.0, lambda: update_status())  # Update every 30 seconds

def create_dashboard():
    """Create the main dashboard UI."""
    with ui.column():
        ui.label('Hammerspace Monitoring Dashboard').classes('text-h4 mb-4')
        
        # Service Status Cards
        with ui.card().classes('mb-4'):
            ui.label('Service Status').classes('text-h6')
            with ui.grid(columns=2):
                update_status()  # Initial update

def main():
    create_dashboard()
    ui.run(title='Hammerspace Monitoring', port=8088, reload=True, host='0.0.0.0')

if __name__ in {"__main__", "__mp_main__"}:
    main()
