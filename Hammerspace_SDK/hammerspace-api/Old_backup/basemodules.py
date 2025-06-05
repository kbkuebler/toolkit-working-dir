import requests
from requests.auth import HTTPBasicAuth
from icecream import ic
import warnings
from typing import Optional, Tuple, Dict, Any, Union
import json
import time

# Suppress only the InsecureRequestWarning from urllib3 needed for verify=False
warnings.filterwarnings(
    'ignore',
    message='Unverified HTTPS request',
    category=requests.packages.urllib3.exceptions.InsecureRequestWarning
)

# --- Keep make_rest_call and read_and_parse_json_body from previous answers ---
def make_rest_call(
    base_url: str,
    path: str,
    method: str = 'GET',
    query_params: Optional[Dict[str, Any]] = None,
    json_data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    auth: Optional[Tuple[str, str]] = None,
    verify_ssl: bool = True
) -> Optional[requests.Response]:
    """Makes a REST API call (implementation from previous answer)."""
    full_url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    request_auth = HTTPBasicAuth(*auth) if auth else None
    request_headers = headers.copy() if headers else {}
    if json_data is not None and 'Content-Type' not in request_headers:
        request_headers['Content-Type'] = 'application/json'
    try:
        response = requests.request(
            method=method.upper(),
            url=full_url,
            params=query_params,
            json=json_data,
            headers=request_headers,
            auth=request_auth,
            verify=verify_ssl
        )
        return response
    except requests.exceptions.RequestException as e:
        ic(f"Request failed for {method} {full_url}: {e}")
        return None
    except Exception as e:
        ic(f"Unexpected error during request to {method} {full_url}: {e}")
        return None

def read_and_parse_json_body(
    response: Optional[requests.Response]
) -> Optional[Any]:
    """Reads and parses JSON body (implementation from previous answer)."""
    if response is None:
        ic("Cannot parse body: Response object is None (request likely failed).")
        return None
    ic(response.request.method, response.request.url)
    ic(f"Status Code: {response.status_code}")
    if response.status_code in (200, 201, 202): # Added 202 for accepted async tasks
        if not response.content:
             ic("Success/Accepted status code but no content in response body.")
             return None
        try:
            parsed_data = response.json()
            ic("Successfully parsed JSON body.")
            return parsed_data
        except json.JSONDecodeError as e:
            ic(f"Failed to decode JSON response body despite status {response.status_code}: {e}")
            ic("Response text snippet:", response.text[:500])
            return None
    else:
        ic(f"Error status code {response.status_code}. Cannot reliably parse body as success JSON.")
        try:
            error_details = response.json()
            ic("Attempted to parse error body as JSON:", error_details)
        except json.JSONDecodeError:
            ic("Error response body (text snippet):", response.text[:500])
        return None

# --- New Function for Asynchronous Task Monitoring ---
def execute_and_monitor_task(
    base_url: str,
    path: str,
    method: str, # POST, PUT, DELETE
    initial_json_data: Optional[Dict[str, Any]] = None,
    initial_query_params: Optional[Dict[str, Any]] = None,
    initial_headers: Optional[Dict[str, str]] = None,
    auth: Optional[Tuple[str, str]] = None,
    verify_ssl: bool = True,
    task_timeout_seconds: int = 300, # Default 5 minutes
    poll_interval_seconds: int = 5
) -> Optional[str]:
    """
    Executes an initial API call (POST, PUT, DELETE) that starts an
    asynchronous task, then monitors the task via its Location header URL
    until it completes or fails, or times out.

    Args:
        base_url: The base URL of the API server.
        path: The API path for the initial call.
        method: The HTTP method for the initial call (POST, PUT, DELETE).
        initial_json_data: JSON payload for the initial call.
        initial_query_params: Query parameters for the initial call.
        initial_headers: Headers for the initial call.
        auth: Tuple (username, password) for Basic Auth.
        verify_ssl: Set to False to disable SSL certificate verification.
        task_timeout_seconds: Max time to wait for the task to complete.
        poll_interval_seconds: How often to poll the task status URL.

    Returns:
        The UUID of the created/modified/relevant object if the task
        completes successfully and a UUID is found in the task's final
        status response (typically in 'uuid' or 'ctxMap.entity-uoid.uuid').
        Returns None if the task fails, times out, or the UUID cannot be found.
    """
    ic(f"Initiating task: {method} {base_url}{path}")
    initial_response = make_rest_call(
        base_url=base_url,
        path=path,
        method=method,
        json_data=initial_json_data,
        query_params=initial_query_params,
        headers=initial_headers,
        auth=auth,
        verify_ssl=verify_ssl
    )

    if initial_response is None:
        ic("Initial API call failed. Cannot monitor task.")
        return None

    # Typically, async tasks are accepted with 202
    if initial_response.status_code != 202:
        ic(f"Initial call did not return 202 Accepted. Status: {initial_response.status_code}")
        ic("Response text:", initial_response.text[:500])
        # You might still get a Location header on other success codes,
        # but 202 is the standard for "I've started the work".
        # If it's 200/201, the operation might have been synchronous.
        if initial_response.status_code in (200, 201):
             parsed_sync_response = read_and_parse_json_body(initial_response)
             if parsed_sync_response and isinstance(parsed_sync_response, dict):
                 return parsed_sync_response.get('uuid') # Or other relevant ID field
        return None


    location_url = initial_response.headers.get('Location')
    if not location_url:
        ic("No 'Location' header found in the initial response. Cannot monitor task.")
        ic("Initial response headers:", initial_response.headers)
        return None

    ic(f"Task initiated. Monitoring Location URL: {location_url}")

    start_time = time.time()
    while (time.time() - start_time) < task_timeout_seconds:
        ic(f"Polling task status at: {location_url}")
        # The location_url is often a full URL, so base_url might not be needed,
        # or it might be a relative path. Adjust as per your API's behavior.
        # Assuming location_url is absolute or relative to the same base_url for simplicity.
        # If location_url is absolute, make_rest_call needs to handle it or
        # we use requests.get directly.
        
        # Determine if location_url is absolute or relative
        if location_url.startswith(('http://', 'https://')):
            task_status_response = requests.get(location_url, auth=HTTPBasicAuth(*auth) if auth else None, verify=verify_ssl)
        else: # Assuming relative to base_url
             task_status_response = make_rest_call(
                base_url=base_url, # Or derive from initial_response.url
                path=location_url, # This path might be absolute from the server root
                method="GET",
                auth=auth,
                verify_ssl=verify_ssl
            )


        if task_status_response is None:
            ic("Failed to get task status. Retrying...")
            time.sleep(poll_interval_seconds)
            continue

        task_data = read_and_parse_json_body(task_status_response)

        if task_data and isinstance(task_data, dict):
            status_message = task_data.get('statusMessage')
            task_status = task_data.get('status') # Some APIs use 'status'
            ic(f"Task status: {status_message or task_status}")

            if status_message == "COMPLETED" or task_status == "COMPLETED":
                ic("Task COMPLETED.")
                # Try to extract UUID from common places
                # Based on your sample output:
                # 1. Top-level 'uuid' (often the task's own UUID)
                # 2. 'ctxMap' -> 'entity-uoid' -> 'uuid' (often the created resource's UUID)
                # 3. 'paramsMap' -> 'uoid' -> 'uuid' (less common for result, but possible)
                
                created_object_uuid = task_data.get('uuid') # Task's own UUID

                if task_data.get('ctxMap') and isinstance(task_data['ctxMap'], dict):
                    entity_uoid = task_data['ctxMap'].get('entity-uoid')
                    if isinstance(entity_uoid, dict) and entity_uoid.get('uuid'):
                        created_object_uuid = entity_uoid['uuid']
                        ic(f"Found entity UUID in ctxMap: {created_object_uuid}")
                        return created_object_uuid
                    elif isinstance(entity_uoid, str) and "uuid=" in entity_uoid: # Handle "Uoid [uuid=..., objectType=...]" string
                        try:
                            uuid_part = entity_uoid.split("uuid=")[1].split(",")[0]
                            created_object_uuid = uuid_part
                            ic(f"Extracted entity UUID from ctxMap string: {created_object_uuid}")
                            return created_object_uuid
                        except IndexError:
                            ic("Could not parse UUID from entity-uoid string in ctxMap")


                if created_object_uuid: # Fallback to task's UUID if specific entity UUID not found
                    ic(f"Returning task UUID as fallback: {created_object_uuid}")
                    return created_object_uuid
                
                ic("Task completed, but no identifiable UUID for the new object found in response.")
                ic("Final task data:", task_data)
                return None # Or task_data.get('uuid') if the task's own UUID is acceptable

            elif status_message == "FAILED" or task_status == "FAILED":
                ic("Task FAILED.")
                ic("Failure details:", task_data)
                return None
            # Add other potential in-progress statuses if your API has them
            elif status_message in ("RUNNING", "PENDING", "IN_PROGRESS") or \
                 task_status in ("RUNNING", "PENDING", "IN_PROGRESS"):
                ic("Task still in progress...")
            else:
                ic(f"Unknown task status: {status_message or task_status}. Continuing to monitor.")


        time.sleep(poll_interval_seconds)

    ic("Task monitoring timed out.")
    return None