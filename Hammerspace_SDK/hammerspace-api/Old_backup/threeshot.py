# your_main_script.py

import logging # Import logging here
from hammerspace import HammerspaceApiClient # Your client
# from icecream import ic # No longer needed for client logs

# --- Basic Logging Configuration ---
# This should be done once, at the beginning of your application.
logging.basicConfig(
    level=logging.DEBUG,  # Set to logging.INFO for less verbose output
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Log to console (stderr by default)
        # You could also add logging.FileHandler("app.log") to log to a file
    ]
)
# ------------------------------------

# Configuration for your Hammerspace cluster
API_BASE_URL = "https://192.168.2.10:8443/mgmt/v1.2/rest"
USERNAME = "admin"
PASSWORD = "Password123!"
VERIFY_SSL = False

# Get a logger for the main script itself, if needed
main_logger = logging.getLogger(__name__)


def main():
    main_logger.info("--- Initializing Hammerspace API Client ---")
    hs_client = HammerspaceApiClient(
        base_url=API_BASE_URL,
        auth=(USERNAME, PASSWORD),
        verify_ssl=VERIFY_SSL
    )

    # Example 1: Get AD Configuration (Simple GET)
    main_logger.info("--- Example 1: GET /shares ---")
    rest_response_obj = hs_client.make_rest_call(path="/shares", method="GET")
    rest_data = hs_client.read_and_parse_json_body(rest_response_obj)
    if rest_data:
        main_logger.info(f"Successfully retrieved AD configuration (first item if list): {rest_data[0]['name'] if isinstance(rest_data, list) and rest_data else rest_data!r}")
    else:
        main_logger.warning("Failed to retrieve AD configuration.")



if __name__ == "__main__":
    main()