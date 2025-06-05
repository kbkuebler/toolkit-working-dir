# hammerspace/client.py  # Origninal

import requests
from requests.auth import HTTPBasicAuth
# from icecream import ic # No longer needed
import warnings
from typing import Optional, Tuple, Dict, Any, Union
import json
import time
import logging # Import the logging module

# Get a logger instance for this module.
# Using __name__ is a common practice, so log messages will be prefixed
# with 'hammerspace.client' if your project structure is 'hammerspace/client.py'.
logger = logging.getLogger(__name__)

# Suppress only the InsecureRequestWarning from urllib3
warnings.filterwarnings(
    'ignore',
    message='Unverified HTTPS request',
    category=requests.packages.urllib3.exceptions.InsecureRequestWarning
)

class HammerspaceApiClient:
    def __init__(self, base_url: str, auth: Optional[Tuple[str, str]] = None, verify_ssl: bool = True):
        """
        Initializes the Hammerspace API Client.
        """
        self.base_url = base_url.rstrip('/')
        self.auth = HTTPBasicAuth(*auth) if auth else None
        self.verify_ssl = verify_ssl
        logger.info(f"HammerspaceApiClient initialized for {self.base_url}")

    def make_rest_call(
        self,
        path: str,
        method: str = 'GET',
        query_params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Optional[requests.Response]:
        """
        Makes a REST API call to a target endpoint using instance settings.
        """
        full_url = f"{self.base_url}/{path.lstrip('/')}"
        
        request_headers = headers.copy() if headers else {}
        if json_data is not None and 'Content-Type' not in request_headers:
            request_headers['Content-Type'] = 'application/json'

        logger.debug(f"Making request: {method.upper()} {full_url}")
        logger.debug(f"Query Params: {query_params!r}") # Use !r for repr
        logger.debug(f"JSON Data: {json_data!r}")
        logger.debug(f"Headers: {request_headers!r}")

        try:
            response = requests.request(
                method=method.upper(),
                url=full_url,
                params=query_params,
                json=json_data,
                headers=request_headers,
                auth=self.auth,
                verify=self.verify_ssl
            )
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {method.upper()} {full_url}: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Unexpected error during request to {method.upper()} {full_url}: {e}", exc_info=True)
            return None

    def read_and_parse_json_body(
        self,
        response: Optional[requests.Response]
    ) -> Optional[Any]:
        """
        Reads and parses JSON body from a requests.Response object.
        """
        if response is None:
            logger.warning("Cannot parse body: Response object is None (request likely failed).")
            return None

        logger.debug(f"Response from: {response.request.method} {response.request.url}")
        logger.debug(f"Status Code: {response.status_code}")

        if response.status_code in (200, 201, 202):
            if not response.content:
                 logger.debug("Success/Accepted status code but no content in response body.")
                 return None
            try:
                parsed_data = response.json()
                logger.debug("Successfully parsed JSON body.")
                # logger.debug(f"Parsed data: {parsed_data!r}") # Optionally log full data
                return parsed_data
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to decode JSON response body despite status {response.status_code}: {e}")
                logger.debug(f"Response text snippet: {response.text[:500]!r}")
                return None
        else:
            logger.warning(f"Error status code {response.status_code}. Cannot reliably parse body as success JSON.")
            try:
                error_details = response.json()
                logger.debug(f"Attempted to parse error body as JSON: {error_details!r}")
            except json.JSONDecodeError:
                logger.debug(f"Error response body (text snippet): {response.text[:500]!r}")
            return None

    def execute_and_monitor_task(
        self,
        path: str,
        method: str,
        initial_json_data: Optional[Dict[str, Any]] = None,
        initial_query_params: Optional[Dict[str, Any]] = None,
        initial_headers: Optional[Dict[str, str]] = None,
        task_timeout_seconds: int = 300,
        poll_interval_seconds: int = 5
    ) -> Optional[str]:
        """
        Executes an initial API call and monitors the resulting asynchronous task.
        """
        logger.info(f"Initiating task via: {method.upper()} {self.base_url}/{path.lstrip('/')}")
        initial_response = self.make_rest_call(
            path=path,
            method=method,
            json_data=initial_json_data,
            query_params=initial_query_params,
            headers=initial_headers
        )

        if initial_response is None:
            logger.error("Initial API call failed. Cannot monitor task.")
            return None

        if initial_response.status_code != 202:
            logger.warning(f"Initial call did not return 202 Accepted. Status: {initial_response.status_code}")
            logger.debug(f"Initial response text: {initial_response.text[:500]!r}" if initial_response.text else "No response text.")
            if initial_response.status_code in (200, 201):
                 parsed_sync_response = self.read_and_parse_json_body(initial_response)
                 if parsed_sync_response and isinstance(parsed_sync_response, dict):
                     sync_uuid = parsed_sync_response.get('uuid')
                     if sync_uuid:
                         logger.info(f"Synchronous success with UUID: {sync_uuid}")
                         return sync_uuid
                     uoid_data = parsed_sync_response.get('uoid')
                     if isinstance(uoid_data, dict) and uoid_data.get('uuid'):
                        sync_uuid_from_uoid = uoid_data.get('uuid')
                        logger.info(f"Synchronous success with UUID from uoid: {sync_uuid_from_uoid}")
                        return sync_uuid_from_uoid
            return None

        location_url = initial_response.headers.get('Location')
        if not location_url:
            logger.warning("No 'Location' header found in the 202 response. Cannot monitor task.")
            logger.debug(f"Initial response headers: {initial_response.headers!r}")
            return None

        logger.info(f"Task initiated. Monitoring Location URL: {location_url}")

        start_time = time.time()
        while (time.time() - start_time) < task_timeout_seconds:
            logger.debug(f"Polling task status at: {location_url}")
            
            task_status_response_obj: Optional[requests.Response] = None
            polling_headers = initial_headers.copy() if initial_headers else {}
            # Ensure 'accept' header for polling if not already set
            if 'accept' not in (key.lower() for key in polling_headers.keys()):
                polling_headers['accept'] = 'application/json'

            if location_url.startswith(('http://', 'https://')):
                try:
                    task_status_response_obj = requests.get(
                        location_url, 
                        auth=self.auth, 
                        verify=self.verify_ssl,
                        headers=polling_headers
                    )
                except requests.exceptions.RequestException as e:
                    logger.warning(f"Polling request failed for {location_url}: {e}", exc_info=True)
            else:
                task_status_response_obj = self.make_rest_call(
                    path=location_url,
                    method="GET",
                    headers=polling_headers
                )

            if task_status_response_obj is None:
                logger.warning("Failed to get task status (request failed). Retrying...")
                time.sleep(poll_interval_seconds)
                continue

            task_data = self.read_and_parse_json_body(task_status_response_obj)

            if task_data and isinstance(task_data, dict):
                status_message = task_data.get('statusMessage')
                task_status = task_data.get('status')
                current_task_state = status_message or task_status
                logger.info(f"Task status: {current_task_state}")

                if current_task_state == "COMPLETED":
                    logger.info("Task COMPLETED.")
                    created_object_uuid = task_data.get('uuid') 

                    if task_data.get('ctxMap') and isinstance(task_data['ctxMap'], dict):
                        entity_uoid_val = task_data['ctxMap'].get('entity-uoid')
                        if isinstance(entity_uoid_val, dict) and entity_uoid_val.get('uuid'):
                            created_object_uuid = entity_uoid_val['uuid']
                            logger.debug(f"Found entity UUID in ctxMap: {created_object_uuid}")
                            return created_object_uuid
                        elif isinstance(entity_uoid_val, str) and "uuid=" in entity_uoid_val:
                            try:
                                uuid_part = entity_uoid_val.split("uuid=")[1].split(",")[0].split("]")[0]
                                created_object_uuid = uuid_part
                                logger.debug(f"Extracted entity UUID from ctxMap string: {created_object_uuid}")
                                return created_object_uuid
                            except IndexError:
                                logger.warning("Could not parse UUID from entity-uoid string in ctxMap")
                    
                    if created_object_uuid:
                        logger.info(f"Returning task's own UUID as primary result: {created_object_uuid}")
                        return created_object_uuid
                    
                    logger.warning("Task completed, but no specific entity UUID found. Check task_data.")
                    logger.debug(f"Final task data: {task_data!r}")
                    return None 

                elif current_task_state == "FAILED":
                    logger.error("Task FAILED.")
                    logger.error(f"Failure details: {task_data!r}")
                    return None
                elif current_task_state in ("RUNNING", "PENDING", "IN_PROGRESS"):
                    logger.debug("Task still in progress...")
                else:
                    logger.info(f"Unknown or intermediate task status: {current_task_state}. Continuing to monitor.")
            else:
                logger.warning("Task data not found or not a dictionary while polling. Retrying...")


            time.sleep(poll_interval_seconds)

        logger.warning("Task monitoring timed out.")
        return None
