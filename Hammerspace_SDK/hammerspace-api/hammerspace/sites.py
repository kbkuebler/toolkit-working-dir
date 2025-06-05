# hammerspace/sites.py
import logging
from typing import Optional, List, Dict, Any, Union

logger = logging.getLogger(__name__)

class SitesClient:
    def __init__(self, api_client: Any):
        """
        Initializes the SitesClient.

        Args:
            api_client: An instance of HammerspaceApiClient.
        """
        self.api_client = api_client
        logger.info("SitesClient initialized using provided OpenAPI spec.")

    def get(
        self,
        identifier: Optional[str] = None,
        **kwargs
    ) -> Union[Optional[List[Dict[str, Any]]], Optional[Dict[str, Any]]]:
        """
        Gets all sites or a specific site by its identifier.

        If 'identifier' is provided, fetches a single site.
        (Corresponds to GET /sites/{identifier} - OpId: getSiteByIdentifier)
        Note: The GET /sites/{identifier} endpoint in the provided spec
              does not list any query parameters, so kwargs are ignored if an
              identifier is provided for this specific call.

        Otherwise, lists all sites.
        (Corresponds to GET /sites - OpId: listSites)
        Optional kwargs for listing:
            spec (str): Filter predicate.
            page (int): Zero-based page number.
            page_size (int): Elements per page. (API name: page.size)
            page_sort (str): Field to sort on. (API name: page.sort)
            page_sort_dir (str): Either 'asc' or 'desc'. (API name: page.sort.dir)
        """
        query_params = {}
        if identifier:
            path = f"/sites/{identifier}"
            logger.info(f"Getting site by identifier: {identifier}")
            # No query parameters are defined for GET /sites/{identifier} in the provided spec.
            # If your actual API supports them, you would process kwargs here.
        else:
            path = "/sites"
            if "spec" in kwargs: query_params["spec"] = kwargs["spec"]
            if "page" in kwargs: query_params["page"] = kwargs["page"]
            if "page_size" in kwargs: query_params["page.size"] = kwargs["page_size"]
            if "page_sort" in kwargs: query_params["page.sort"] = kwargs["page_sort"]
            if "page_sort_dir" in kwargs: query_params["page.sort.dir"] = kwargs["page_sort_dir"]
            logger.info(f"Listing all sites with effective query params: {query_params}")
        
        response = self.api_client.make_rest_call(path=path, method="GET", query_params=query_params)
        return self.api_client.read_and_parse_json_body(response)

    # Based on the provided OpenAPI spec, there are no POST, PUT, or DELETE operations
    # defined under the 'sites' tag. If these operations exist under a different tag
    # or were omitted from the snippet, they would be added here.

    # Example of how a create_site method would look if the endpoint existed:
    # def create_site(
    #     self, site_data: Dict[str, Any], monitor_task: bool = True, task_timeout_seconds: int = 300, **kwargs
    # ) -> Union[Optional[str], Optional[Dict[str, Any]]]:
    #     """
    #     Creates a new site. (Hypothetical POST /sites)
    #     """
    #     path = "/sites"
    #     query_params = {} # Add if POST /sites has query params
    #     logger.info(f"Creating site with data: {site_data}, query_params: {query_params}")
    #     return self.api_client.execute_and_monitor_task(
    #         path=path, method="POST", initial_json_data=site_data, initial_query_params=query_params,
    #         monitor_task=monitor_task, task_timeout_seconds=task_timeout_seconds
    #     )

    # Example of how an update_site_by_identifier method would look:
    # def update_site_by_identifier(
    #     self, identifier: str, site_data: Dict[str, Any],
    #     monitor_task: bool = True, task_timeout_seconds: int = 300, **kwargs
    # ) -> Union[Optional[str], Optional[Dict[str, Any]]]:
    #     """
    #     Updates an existing site by its identifier. (Hypothetical PUT /sites/{identifier})
    #     """
    #     path = f"/sites/{identifier}"
    #     query_params = {} # Add if PUT /sites/{id} has query params
    #     logger.info(f"Updating site '{identifier}' with data: {site_data}, query_params: {query_params}")
    #     return self.api_client.execute_and_monitor_task(
    #         path=path, method="PUT", initial_json_data=site_data, initial_query_params=query_params,
    #         monitor_task=monitor_task, task_timeout_seconds=task_timeout_seconds
    #     )

    # Example of how a delete_site_by_identifier method would look:
    # def delete_site_by_identifier(
    #     self, identifier: str, monitor_task: bool = True, task_timeout_seconds: int = 300, **kwargs
    # ) -> Union[Optional[str], Optional[Dict[str, Any]]]:
    #     """
    #     Deletes a site by its identifier. (Hypothetical DELETE /sites/{identifier})
    #     """
    #     path = f"/sites/{identifier}"
    #     query_params = {} # Add if DELETE /sites/{id} has query params (e.g., 'force')
    #     if "force" in kwargs: query_params["force"] = str(kwargs["force"]).lower()
    #     logger.info(f"Deleting site '{identifier}' with query_params: {query_params}")
    #     return self.api_client.execute_and_monitor_task(
    #         path=path, method="DELETE", initial_query_params=query_params,
    #         monitor_task=monitor_task, task_timeout_seconds=task_timeout_seconds
    #     )
