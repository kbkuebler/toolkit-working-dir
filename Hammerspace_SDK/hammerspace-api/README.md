# Hammerspace Python API Client

A Python client library for interacting with the Hammerspace sys-mgmt API. This library provides a convenient way to manage various Hammerspace resources programmatically.

## Features

*   **Comprehensive Resource Management**: Covers a wide range of Hammerspace resources including:
    *   Authentication (Login)
    *   Active Directory (AD), LDAP, NIS, IdP
    *   Users, User Groups, Roles
    *   Shares, Share Snapshots, Share Participants, Share Replications
    *   Storage Volumes (File & Object), Logical Volumes, Volume Groups
    *   Nodes, Network Interfaces, Static Routes, Subnet Gateways
    *   Objectives, Schedules, Snapshot Retentions
    *   S3 Servers, Object Stores
    *   Tasks, Events, Notifications
    *   System Settings, System Info, Software Updates, Versions
    *   Metrics, Reports, Logging (Syslog)
    *   And many more...
*   **Standardized Client Interface**: Each resource type has its own client (e.g., `UsersClient`, `SharesClient`) with consistent methods:
    *   `get(identifier=None, **kwargs)`: For listing resources or fetching a specific resource by ID.
    *   `create_<resource>(data, **kwargs)`: For creating new resources.
    *   `update_<resource>_by_identifier(identifier, data, **kwargs)`: For updating existing resources.
    *   `delete_<resource>_by_identifier(identifier, **kwargs)`: For deleting resources.
*   **Asynchronous Task Monitoring**: Built-in support for operations that trigger asynchronous tasks on the Hammerspace system. The `execute_and_monitor_task` helper polls task status until completion, failure, or timeout.
*   **Flexible Parameter Handling**: Uses `**kwargs` for optional query parameters and body fields, making method calls clean and adaptable to API changes.
*   **Session Management**: Uses `requests.Session()` for persistent connections and cookie handling.
*   **SSL Verification Control**: Allows enabling or disabling SSL certificate verification.
*   **Logging**: Integrated logging for requests and responses to aid in debugging.

## Installation

Currently, this library is intended to be used by including the `hammerspace` directory directly in your project.

```bash
# (No pip install command yet, add the 'hammerspace' directory to your Python path)
# For example, if your project structure is:
# my_project/
# |-- main_script.py
# |-- hammerspace/
#     |-- __init__.py
#     |-- users.py
#     |-- ... (other client files)

# You can import it in main_script.py as:
# from hammerspace import HammerspaceApiClient

** Usage

** Initializing the Client

* First, import and initialize the main HammerspaceApiClient:

'''python
from hammerspace import HammerspaceApiClient
import logging

# Optional: Configure logging for your application to see library logs
# logging.basicConfig(level=logging.DEBUG) # For verbose output
# logging.basicConfig(level=logging.INFO)  # For standard output

HS_BASE_URL = "https://<your-anvil-ip>:8443/mgmt/v1.2/rest"
HS_USERNAME = "your_username"
HS_PASSWORD = "your_password"

try:
    client = HammerspaceApiClient(
        base_url=HS_BASE_URL,
        username=HS_USERNAME,
        password=HS_PASSWORD,
        verify_ssl=False,  # Set to True in production with valid certificates
        accept_eula=True   # May be required for the first login
    )
    print("Successfully connected to Hammerspace API.")
except Exception as e:
    print(f"Failed to initialize Hammerspace client: {e}")
    exit()

# List all users
try:
    users = client.users.get(page_size=10)
    if users:
        for user in users:
            print(f"User: {user.get('username')}, UUID: {user.get('uuid')}")
except Exception as e:
    print(f"Error listing users: {e}")

# Get a specific share by its name or UUID
try:
    share_identifier = "my-test-share"
    share = client.shares.get(identifier=share_identifier)
    if share:
        print(f"Share details for '{share_identifier}': {share.get('exportPath')}")
    else:
        print(f"Share '{share_identifier}' not found.")
except Exception as e:
    print(f"Error getting share '{share_identifier}': {e}")

# Create a new resource (e.g., a new role)
try:
    new_role_data = {
        "name": "ReadOnlyRole",
        "comment": "Role with read-only permissions",
        "permissions": ["READ_SYSTEM_CONFIG"] # Example permission
    }
    # Assuming create_role returns the created object or task info
    # For operations that might be long-running, monitor_task=True is recommended
    role_creation_result = client.roles.create_role(role_data=new_role_data, monitor_task=True)
    
    if role_creation_result:
        if isinstance(role_creation_result, str): # Task ID returned
            print(f"Role creation task started: {role_creation_result}")
            # You might want to poll client.tasks.get(identifier=role_creation_result)
        elif isinstance(role_creation_result, dict) and role_creation_result.get("status") == "SUCCEEDED":
            print(f"Role created successfully: {role_creation_result.get('result', {}).get('name')}")
        elif isinstance(role_creation_result, dict): # Synchronous creation or failed task
             print(f"Role creation result/status: {role_creation_result}")
        else:
            print(f"Role creation initiated, result: {role_creation_result}")

except Exception as e:
    print(f"Error creating role: {e}")

# Delete a resource (e.g., a user group)
try:
    group_to_delete_id = "some-group-uuid"
    # monitor_task=True is good for delete operations as well
    delete_result = client.user_groups.delete_user_group_by_identifier(
        identifier=group_to_delete_id, 
        monitor_task=True
    )
    if delete_result:
         if isinstance(delete_result, dict) and delete_result.get("status") == "SUCCEEDED":
            print(f"User group '{group_to_delete_id}' deleted successfully.")


        else:
            print(f"User group deletion task status/result: {delete_result}")
except Exception as e:
    print(f"Error deleting user group '{group_to_delete_id}': {e}")
'''

