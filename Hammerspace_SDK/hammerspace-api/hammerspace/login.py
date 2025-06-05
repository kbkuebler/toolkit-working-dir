# hammerspace/login.py
import logging
from typing import Optional, Dict, Any
import requests # Keep for direct call

logger = logging.getLogger(__name__)

class LoginClient:
    def __init__(self, api_client: Any):
        self.api_client = api_client

    def login_user(self, username: str, password: str, **kwargs) -> bool:
        """
        Login user. (POST /login) - OpId: loginUser
        Uses application/x-www-form-urlencoded.

        Args:
            username (str): The username.
            password (str): The password.
            **kwargs: Optional keyword arguments.
                accept_eula (bool): (API form field: acceptEula)

        Returns:
            True on successful login, False otherwise.
        """
        path = "/login"
        form_data: Dict[str, Any] = { # Ensure type for form_data
            "username": username,
            "password": password
        }
        if "accept_eula" in kwargs:
            # API spec shows boolean, requests 'data' param handles bools appropriately for forms
            form_data["acceptEula"] = kwargs["accept_eula"]

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
        logger.info(f"Attempting login for user '{username}'.")
        try:
            full_url = f"{self.api_client.base_url}/{path.lstrip('/')}"
            # Using requests.post directly for x-www-form-urlencoded
            response = requests.post(
                full_url,
                data=form_data,
                headers=headers,
                verify=self.api_client.verify_ssl
                # Session cookies will be handled by the requests library if set by server
            )
            logger.debug(f"Login response status: {response.status_code}")
            # OpenAPI spec says "default: successful operation, content: {}"
            # Typically, a 2xx status code indicates success for login.
            if 200 <= response.status_code < 300:
                logger.info(f"Login successful for user '{username}'. Status: {response.status_code}")
                # If your HammerspaceApiClient uses a requests.Session, cookies are now stored.
                return True
            else:
                logger.warning(f"Login failed for user '{username}'. Status: {response.status_code}, Body: {response.text[:200]}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Login request failed for user '{username}': {e}", exc_info=True)
            return False
        except Exception as e: # Catch any other unexpected errors
            logger.error(f"Unexpected error during login for user '{username}': {e}", exc_info=True)
            return False