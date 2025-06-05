# hammerspace/syslog.py
import logging
from typing import Optional, List, Dict, Any, Union

logger = logging.getLogger(__name__)

class SyslogClient:
    def __init__(self, api_client: Any):
        self.api_client = api_client
        logger.info("SyslogClient initialized using provided OpenAPI spec.")

    def get(
        self,
        identifier: Optional[str] = None,
        **kwargs
    ) -> Union[Optional[List[Dict[str, Any]]], Optional[Dict[str, Any]]]:
        """
        Gets all syslog configurations or a specific one by its identifier.

        If 'identifier' is provided, fetches a single syslog configuration.
        (Corresponds to GET /syslog/{identifier} - OpId: getSyslogConfigurationByIdentifier)

        Otherwise, lists all syslog configurations.
        (Corresponds to GET /syslog - OpId: listSyslogConfiguration)
        Optional kwargs for listing: spec, page, page.size, page.sort, page.sort.dir
        """
        query_params = {}
        if identifier:
            path = f"/syslog/{identifier}"
            logger.info(f"Getting syslog configuration by identifier: {identifier}")
            # No query params for GET /syslog/{identifier} in spec
        else:
            path = "/syslog"
            if "spec" in kwargs: query_params["spec"] = kwargs["spec"]
            if "page" in kwargs: query_params["page"] = kwargs["page"]
            if "page_size" in kwargs: query_params["page.size"] = kwargs["page_size"]
            if "page_sort" in kwargs: query_params["page.sort"] = kwargs["page_sort"]
            if "page_sort_dir" in kwargs: query_params["page.sort.dir"] = kwargs["page_sort_dir"]
            logger.info(f"Listing syslog configurations with effective query params: {query_params}")
        
        response = self.api_client.make_rest_call(path=path, method="GET", query_params=query_params)
        return self.api_client.read_and_parse_json_body(response) # Returns SyslogView or List

    def create_syslog_configuration(
        self,
        syslog_data: Dict[str, Any], # requestBody is BaseEntityView, implies fields for SyslogView
        monitor_task: bool = False, # Spec says 200 OK
        task_timeout_seconds: int = 300,
        **kwargs
    ) -> Union[Optional[str], Optional[Dict[str, Any]]]:
        """
        Configures syslog.
        (Corresponds to POST /syslog - OpId: createSyslogConfiguration)
        """
        path = "/syslog"
        query_params = {} # No query params for POST in spec
        logger.info(f"Creating syslog configuration with data: {syslog_data}")
        if monitor_task:
            return self.api_client.execute_and_monitor_task(
                path=path, method="POST", initial_json_data=syslog_data, initial_query_params=query_params,
                monitor_task=monitor_task, task_timeout_seconds=task_timeout_seconds
            )
        else:
            response = self.api_client.make_rest_call(path=path, method="POST", json_data=syslog_data, query_params=query_params)
            return self.api_client.read_and_parse_json_body(response) # Returns SyslogView

    def update_syslog_configuration_by_identifier(
        self,
        identifier: str,
        syslog_data: Dict[str, Any], # requestBody is SyslogView
        monitor_task: bool = False, # Spec says 200 OK
        task_timeout_seconds: int = 300,
        **kwargs
    ) -> Union[Optional[str], Optional[Dict[str, Any]]]:
        """
        Updates an existing syslog configuration by its identifier.
        (Corresponds to PUT /syslog/{identifier} - OpId: updateSyslogConfigurationByIdentifier)
        """
        path = f"/syslog/{identifier}"
        query_params = {} # No query params for PUT in spec
        logger.info(f"Updating syslog configuration '{identifier}' with data: {syslog_data}")
        if monitor_task:
            return self.api_client.execute_and_monitor_task(
                path=path, method="PUT", initial_json_data=syslog_data, initial_query_params=query_params,
                monitor_task=monitor_task, task_timeout_seconds=task_timeout_seconds
            )
        else:
            response = self.api_client.make_rest_call(path=path, method="PUT", json_data=syslog_data, query_params=query_params)
            return self.api_client.read_and_parse_json_body(response) # Returns SyslogView

    def delete_syslog_configuration_by_identifier(
        self,
        identifier: str,
        monitor_task: bool = False, # Spec says 200 OK
        task_timeout_seconds: int = 300,
        **kwargs
    ) -> Union[Optional[str], Optional[Dict[str, Any]]]:
        """
        Deletes a syslog configuration by its identifier.
        (Corresponds to DELETE /syslog/{identifier} - OpId: deleteSyslogConfigurationByIdentifier)
        """
        path = f"/syslog/{identifier}"
        query_params = {} # No query params for DELETE in spec
        logger.info(f"Deleting syslog configuration '{identifier}'")
        if monitor_task:
            return self.api_client.execute_and_monitor_task(
                path=path, method="DELETE", initial_query_params=query_params,
                monitor_task=monitor_task, task_timeout_seconds=task_timeout_seconds
            )
        else:
            response = self.api_client.make_rest_call(path=path, method="DELETE", query_params=query_params)
            return self.api_client.read_and_parse_json_body(response) # Returns SyslogView