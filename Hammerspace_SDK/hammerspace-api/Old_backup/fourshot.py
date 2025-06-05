# your_main_script.py
import logging
from hammerspace import HammerspaceApiClient, SharesClient, NodesClient, RolesClient, EventsClient #, UsersClient

# Basic Logging Configuration
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

main_logger = logging.getLogger(__name__)

# Configuration
API_BASE_URL = "https://192.168.2.10:8443/mgmt/v1.2/rest" # Your actual URL
USERNAME = "admin"
PASSWORD = "Password123!"
VERIFY_SSL = False

def main():
    main_logger.info("--- Initializing Hammerspace API Client ---")
    base_client = HammerspaceApiClient(
        base_url=API_BASE_URL,
        auth=(USERNAME, PASSWORD),
        verify_ssl=VERIFY_SSL
    )

    # Initialize resource-specific clients
    shares_api = SharesClient(base_client)
    # nodes_api = NodesClient(base_client)
    # roles_api = RolesClient(base_client)
    # events_api = EventsClient(base_client)
    # # users_api = UsersClient(base_client) # When implemented

    # # --- Shares Example ---
    # main_logger.info("--- Listing Shares ---")
    # all_shares = shares_api.list_shares(page_size=5)
    # if all_shares:
    #     main_logger.info(f"Found {len(all_shares)} shares (first 5 or less):")
    #     for share in all_shares:
    #         main_logger.debug(f"  Share Name: {share.get('name')}, UUID: {share.get('uoid', {}).get('uuid')}")
    # else:
    #     main_logger.warning("Could not list shares or no shares found.")

    # # --- Nodes Example ---
    # main_logger.info("--- Listing Nodes ---")
    # all_nodes = nodes_api.list_nodes(page_size=2)
    # if all_nodes:
    #     main_logger.info(f"Found {len(all_nodes)} nodes (first 2 or less):")
    #     for node in all_nodes:
    #         main_logger.debug(f"  Node Name: {node.get('name')}, UUID: {node.get('uoid', {}).get('uuid')}")

    # # --- Roles Example ---
    # main_logger.info("--- Listing Roles ---")
    # all_roles = roles_api.list_roles(page_size=3)
    # if all_roles:
    #     main_logger.info(f"Found {len(all_roles)} roles (first 3 or less):")
    #     for role in all_roles:
    #         main_logger.debug(f"  Role Name: {role.get('name')}")
            
    # # --- Events Example ---
    # main_logger.info("--- Listing Events ---")
    # latest_events = events_api.list_events(page_size=5, page_sort="created", page_sort_dir="desc")
    # if latest_events:
    #     main_logger.info(f"Found {len(latest_events)} recent events:")
    #     for event in latest_events:
    #         main_logger.debug(f"  Event ID: {event.get('uoid',{}).get('uuid')}, Message: {event.get('message')}")


    main_logger.info("--- Attempting to Create a Share ---")
    for x in range(100):

        share_payload = {
            "comment": "My Module Test Share via Client",
            "name": f"moduleClientShare0{x}",
            "path": f"/moduleClientShare0{x}",
            "exportOptions": [{"subnet": "*", "accessPermissions": "RW", "rootSquash": False, "insecure": False}]
        }
        created_share_task_uuid = shares_api.create_share(share_payload)
        if created_share_task_uuid:
            main_logger.info(f"Share creation task initiated successfully. Task/Object UUID: {created_share_task_uuid}")
        else:
            main_logger.error("Share creation failed or was not asynchronous as expected.")


if __name__ == "__main__":
    main()