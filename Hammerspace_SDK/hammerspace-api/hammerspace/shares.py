# hammerspace/shares.py
import logging
from typing import Optional, List, Dict, Any, Union
logger = logging.getLogger(__name__)

class SharesClient:
    def __init__(self, api_client: Any):
        self.api_client = api_client

    def get(
        self,
        identifier: Optional[str] = None,
        **kwargs
    ) -> Union[Optional[List[Dict[str, Any]]], Optional[Dict[str, Any]]]:
        """
        Gets all shares or a specific share by its identifier (UUID or name).

        If 'identifier' is provided, fetches a single share.
        (Assumes GET /shares/{identifier} - NOT in provided OpenAPI snippet)

        Otherwise, lists all shares.
        (Corresponds to GET /shares - OpId: ListShares)
        Optional kwargs for listing: spec (str), page (int), page_size (int),
                                     page_sort (str), page_sort_dir (str)
        """
        query_params = {}
        if identifier:
            path = f"/shares/{identifier}" 
            logger.warning(
                f"get_share by id: Attempting GET from '{path}'. "
            )

        else:
            path = "/shares"
            if "spec" in kwargs: query_params["spec"] = kwargs["spec"]
            if "page" in kwargs: query_params["page"] = kwargs["page"]
            if "page_size" in kwargs: query_params["page.size"] = kwargs["page_size"]
            if "page_sort" in kwargs: query_params["page.sort"] = kwargs["page_sort"]
            if "page_sort_dir" in kwargs: query_params["page.sort.dir"] = kwargs["page_sort_dir"]
            logger.info(f"Listing shares with effective query params: {query_params}")
        
        response = self.api_client.make_rest_call(path=path, method="GET", query_params=query_params)
        return self.api_client.read_and_parse_json_body(response)

    def create_share(
        self, share_data: Dict[str, Any], monitor_task: bool = True, task_timeout_seconds: int = 300
    ) -> Union[Optional[str], Optional[Dict[str, Any]]]:
        """
        Creates a new share.
        (Assumes POST /shares - NOT in provided OpenAPI snippet)
        """
        assumed_path = "/shares" # THIS IS AN ASSUMPTION
        logger.warning(
            f"create_share: Attempting POST to '{assumed_path}'. "
        )
        # No query params assumed for create
        return self.api_client.execute_and_monitor_task(
            path=assumed_path, method="POST", initial_json_data=share_data,
            monitor_task=monitor_task, task_timeout_seconds=task_timeout_seconds
        )

    def update_share(
        self, identifier: str, share_data: Dict[str, Any],
        monitor_task: bool = True, task_timeout_seconds: int = 300
    ) -> Union[Optional[str], Optional[Dict[str, Any]]]:
        """
        Updates a specific share by its identifier.
        (Assumes PUT /shares/{identifier})
        """
        assumed_path = f"/shares/{identifier}" 
        logger.warning(
            f"update_share_by_id: Attempting PUT to '{assumed_path}'. "
        )
        # No query params assumed for update
        return self.api_client.execute_and_monitor_task(
            path=assumed_path, method="PUT", initial_json_data=share_data,
            monitor_task=monitor_task, task_timeout_seconds=task_timeout_seconds
        )

    def delete_share(
        self, identifier: str, monitor_task: bool = True, task_timeout_seconds: int = 300, **kwargs
    ) -> Union[Optional[str], Optional[Dict[str, Any]]]:
        """
        Deletes a specific share by its identifier.
        (Assumes DELETE /shares/{identifier} - NOT in provided OpenAPI snippet, based on prior examples)
        Optional kwargs for query parameters:
            delete_delay (str): (API name: delete-delay, default "0")
            delete_path (bool): (API name: delete-path, default True)
        """
        assumed_path = f"/shares/{identifier}" # THIS IS AN ASSUMPTION
        logger.warning(
            f"delete_share_by_id: Attempting DELETE to '{assumed_path}'. "
        )
        query_params = {}
        # Set defaults if not provided in kwargs, matching your previous cURL example logic
        query_params["delete-delay"] = str(kwargs.get("delete_delay", "0"))
        query_params["delete-path"] = str(kwargs.get("delete_path", True)).lower()
        
        return self.api_client.execute_and_monitor_task(
            path=assumed_path, method="DELETE", initial_query_params=query_params,
            initial_headers={"accept": "application/json"}, # As per your cURL
            monitor_task=monitor_task, task_timeout_seconds=task_timeout_seconds
        )