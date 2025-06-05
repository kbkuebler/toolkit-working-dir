
import logging
from hammerspace import HammerspaceApiClient, SharesClient, NodesClient, RolesClient, EventsClient, UsersClient

# Basic Logging Configuration
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

main_logger = logging.getLogger(__name__)

# Configuration
API_BASE_URL = "https://192.168.2.11:8443/mgmt/v1.2/rest" # Your actual URL
USERNAME = "admin"
PASSWORD = "Password123!"
VERIFY_SSL = False
MONITOR_TASK= False

def main():
    main_logger.info("--- Initializing Hammerspace API Client ---")
    base_client = HammerspaceApiClient(
        base_url=API_BASE_URL,
        auth=(USERNAME, PASSWORD),
        verify_ssl=VERIFY_SSL
    )

    # Initialize resource-specific clients
    shares_api = SharesClient(base_client)

    main_logger.info("--- Attempting to Create a Share ---")
    for x in range(10):

        share_payload = {
            "comment": "My Module Test Share via Client",
            "name": f"moduleClientShare0{x}",
            "path": f"/moduleClientShare0{x}",
            "exportOptions": [{"subnet": "*", "accessPermissions": "RW", "rootSquash": False, "insecure": False}]
        }
        created_share_task_uuid = shares_api.create_share(share_payload, monitor_task=MONITOR_TASK)
        if created_share_task_uuid:
            main_logger.info(f"Share creation task initiated successfully. Task/Object UUID: {created_share_task_uuid}")
        else:
            main_logger.error("Share creation failed or was not asynchronous as expected.")


if __name__ == "__main__":
    main()
