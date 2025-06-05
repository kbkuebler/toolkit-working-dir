# your_main_script.py
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

def main():
    main_logger.info("--- Initializing Hammerspace API Client ---")
    base_client = HammerspaceApiClient(
        base_url=API_BASE_URL,
        auth=(USERNAME, PASSWORD),
        verify_ssl=VERIFY_SSL
    )

    # Initialize resource-specific clients
    shares_api = SharesClient(base_client)

    # # --- Shares Example ---
    main_logger.info("--- Listing Shares ---")
    all_shares = shares_api.list_shares(spec='name=neq=root')
    if all_shares:
        main_logger.info(f"Found {len(all_shares)} shares (first 5 or less):")
        for share in all_shares:
            shares_api.delete_share_by_id(identifier=share.get('uoid', {}).get('uuid'),monitor_task=False)
            main_logger.debug(f" Removing Share Name: {share.get('name')}, UUID: {share.get('uoid', {}).get('uuid')}")
    else:
        main_logger.warning("Could not list shares or no shares found.")


if __name__ == "__main__":
    main()
