import requests
from requests.auth import HTTPBasicAuth
from icecream import ic
import warnings
from typing import Optional, Tuple, Dict, Any
import json # Import json for JSONDecodeError

# Suppress only the InsecureRequestWarning from urllib3 needed for verify=False
warnings.filterwarnings(
    'ignore',
    message='Unverified HTTPS request',
    category=requests.packages.urllib3.exceptions.InsecureRequestWarning
)

# (Keep the make_rest_call function from the previous answer)
warnings.filterwarnings(
    'ignore',
    message='Unverified HTTPS request',
    category=requests.packages.urllib3.exceptions.InsecureRequestWarning
)

def make_rest_call(
    base_url: str,
    path: str,
    method: str = 'GET',
    query_params: Optional[Dict[str, Any]] = None,
    json_data: Optional[Dict[str, Any]] = None, # Parameter for JSON body data
    headers: Optional[Dict[str, str]] = None,
    auth: Optional[Tuple[str, str]] = None,
    verify_ssl: bool = True
) -> Optional[requests.Response]:
    """
    Makes a REST API call to a target endpoint.

    Handles different HTTP methods, query parameters, JSON body data,
    custom headers, optional basic authentication, and optional SSL
    certificate verification disabling.

    Args:
        base_url: The base URL of the API server (e.g., from servers list).
        path: The specific API path (e.g., '/ad/{identifier}').
        method: The HTTP method ('GET', 'POST', 'PUT', 'DELETE', etc.).
        query_params: Dictionary of query parameters to append to the URL.
        json_data: Dictionary payload for POST/PUT/PATCH requests (sent as JSON).
        headers: Dictionary of custom HTTP headers.
        auth: Tuple containing (username, password) for Basic Auth.
        verify_ssl: Set to False to disable SSL certificate verification.

    Returns:
        A requests.Response object if the call was initiated successfully,
        otherwise None if a request exception occurred.
    """
    full_url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    request_auth = HTTPBasicAuth(*auth) if auth else None

    # Ensure Content-Type is set to application/json if json_data is provided
    # and the user hasn't explicitly set a different Content-Type
    request_headers = headers.copy() if headers else {}
    if json_data is not None and 'Content-Type' not in request_headers:
        request_headers['Content-Type'] = 'application/json'

    try:
        response = requests.request(
            method=method.upper(), # Ensure method is uppercase
            url=full_url,
            params=query_params,
            json=json_data,       # Pass the dictionary here for JSON body
            headers=request_headers, # Use potentially updated headers
            auth=request_auth,
            verify=verify_ssl
        )
        # We don't raise for status here, let the parsing function handle it
        return response
    except requests.exceptions.RequestException as e:
        ic(f"Request failed for {method} {full_url}: {e}")
        return None
    except Exception as e:
        # Catch any other unexpected errors during request setup
        ic(f"Unexpected error during request to {method} {full_url}: {e}")
        return None


def read_and_parse_json_body(
    response: Optional[requests.Response]
) -> Optional[Any]:
    """
    Reads and parses the JSON body from a requests.Response object.

    Checks for successful status codes (200, 201). If successful,
    attempts to parse and return the JSON body using response.json().
    Logs errors using icecream if the status is bad or parsing fails.

    Args:
        response: The requests.Response object.

    Returns:
        The parsed JSON data (dict, list, etc.) on success,
        otherwise None.
    """
    if response is None:
        ic("Cannot parse body: Response object is None (request likely failed).")
        return None

    # Log context for debugging
    ic(response.request.method, response.request.url)
    ic(f"Status Code: {response.status_code}")

    # Check for successful status codes
    if response.status_code in (200, 201):
        # Check if there's actually content to parse
        if not response.content:
             ic("Success status code but no content in response body.")
             return None # Or {} or [] depending on expected type

        try:
            # --- The core step: Read and parse the JSON body ---
            parsed_data = response.json()
            # ----------------------------------------------------
            ic("Successfully parsed JSON body.")
            # ic(parsed_data) # Uncomment to print the parsed data structure
            return parsed_data
        # Catch error if the body wasn't valid JSON
        except json.JSONDecodeError as e: # More specific error type
            ic(f"Failed to decode JSON response body despite status {response.status_code}: {e}")
            ic("Response text snippet:", response.text[:500])
            return None
    else:
        # Handle non-success status codes
        ic(f"Error status code {response.status_code}. Cannot reliably parse body as success JSON.")
        # Optionally try to parse error details if they might be JSON
        try:
            error_details = response.json()
            ic("Attempted to parse error body as JSON:", error_details)
        except json.JSONDecodeError:
            ic("Error response body (text snippet):", response.text[:500])
        return None

def print_nested_data_references(data: Any, current_path: str = "share_data"):
    """
    Recursively traverses a nested data structure (dicts and lists)
    and prints the Python access path for each non-container value.

    Args:
        data: The current piece of data (dict, list, or simple value).
        current_path: The string representing the Python path to reach 'data'.
    """
    if isinstance(data, dict):
        # If it's a dictionary, iterate through key-value pairs
        if not data: # Handle empty dict
             print(f"{current_path} => {{}}")
        else:
            for key, value in data.items():
                # Construct the path for the next level (assuming string keys)
                # Use repr(key) if keys might not be simple strings
                next_path = f"{current_path}['{key}']"
                print_nested_data_references(value, next_path)
    elif isinstance(data, list):
        # If it's a list, iterate through elements with index
        if not data: # Handle empty list
            print(f"{current_path} => []")
        else:
            for index, value in enumerate(data):
                # Construct the path for the next level
                next_path = f"{current_path}[{index}]"
                print_nested_data_references(value, next_path)
    else:
        # Base case: It's a simple value (not dict or list)
        # Use repr() to get a string representation including quotes for strings
        print(f"{current_path} => {repr(data)}")

# --- Example Usage ---

# Configuration (replace with your actual values)
# Select a server URL from your openapi yaml
API_BASE_URL = "https://192.168.2.10:8443/mgmt/v1.2/rest"
USERNAME = "admin" # Replace or set to None if no auth
PASSWORD = "Password123!" # Replace or set to None if no auth
VERIFY_SSL_CERT = False # Set to False for self-signed certs

SHARE_NAME = "Myshare"
#CREATE_BODY = f'{{"comment": "share Comment","name": "{SHARE_NAME}","path": "/{SHARE_NAME}","exportOptions": [{{subnet": "*","accessPermissions": "RO","rootSquash": true,"insecure": false}}]}}'
#CREATE_BODY = f'{{"comment": "share Comment","name": "{SHARE_NAME}","path": "/{SHARE_NAME}"}}'
#CREATE_BODY = """{"comment": "share Comment","name": "Myshare","path": "/Myshare","exportOptions": [{"subnet": "*","accessPermissions": "RO","rootSquash": true,"insecure": false}]}"""
create_payload_dict = {
    "comment": "share Comment",
    "name": "Myshare",
    "path": "/Myshare", # Ensure this path is what the server expects for a new share
    "exportOptions": [{
        "subnet": "*",
        "accessPermissions": "RO",
        "rootSquash": True, # Python boolean
        "insecure": False   # Python boolean
    }]
}

CREATE_BODY = create_payload_dict

print("\n--- Example 1: Successful Put with JSON body ---")
response_ok = make_rest_call(
    base_url=API_BASE_URL,
    path="/shares",
    method="post",
    verify_ssl=VERIFY_SSL_CERT,
    json_data = CREATE_BODY,
    auth=(USERNAME, PASSWORD) if USERNAME else None
)

json_data_ok = read_and_parse_json_body(response_ok)

if json_data_ok:
    print("Successfully read and parsed JSON body:")
    print_nested_data_references(json_data_ok)
else:
    print("Failed to get or parse JSON body.")





# Example 2: Get specific AD config (GET with path parameter)
#print("\n--- Example 2: GET /ad/{identifier} ---")
#ad_identifier = "your_ad_identifier" # Replace with a real identifier
#ad_specific_response = make_rest_call(
#    base_url=API_BASE_URL,
#    path=f"/ad/{ad_identifier}", # Use f-string for path params
#    method="GET",
#    auth=(USERNAME, PASSWORD) if USERNAME else None,
#    verify_ssl=VERIFY_SSL_CERT
#)
#ad_specific_data = parse_json_response(ad_specific_response)
#if ad_specific_data:
#    print(f"Successfully retrieved AD config for {ad_identifier}.")
#    # print(ad_specific_data) # Uncomment to see the data
#else:
#    print(f"Failed to retrieve AD config for {ad_identifier}.")
#
## Example 3: Create Antivirus Service (POST with JSON body)
#print("\n--- Example 3: POST /antivirus ---")
#new_av_config = {
#  "name": "MyNewAVService",
#  "comment": "Created via API",
#  "enabled": True,
#  "address": "192.168.5.100", # Example address
#  "port": 1344 # Example port
#  # Add other required fields based on AntivirusView schema
#}
#av_create_response = make_rest_call(
#    base_url=API_BASE_URL,
#    path="/antivirus",
#    method="POST",
#    json_data=new_av_config,
#    auth=(USERNAME, PASSWORD) if USERNAME else None,
#    verify_ssl=VERIFY_SSL_CERT
#)
#created_av_data = parse_json_response(av_create_response)
#if created_av_data:
#    print("Successfully created Antivirus service.")
#    # print(created_av_data) # Uncomment to see the data
#else:
#    print("Failed to create Antivirus service.")
#
## Example 4: Triggering an error (e.g., non-existent path)
#print("\n--- Example 4: GET /non-existent-path ---")
#error_response = make_rest_call(
#    base_url=API_BASE_URL,
#    path="/non-existent-path-for-sure",
#    method="GET",
#    auth=(USERNAME, PASSWORD) if USERNAME else None,
#    verify_ssl=VERIFY_SSL_CERT
#)
#error_data = parse_json_response(error_response)
#if not error_data:
#    print("Correctly handled error for non-existent path.")
#