"""
Braze API client for campaign triggering and campaign management.
Provides methods to build recipients and send campaign messages to Braze.
"""
import logging
from typing import Any, Dict, List, Optional, Union

import requests
from braze.constants import BrazeAPIEndpoints

logger = logging.getLogger(__name__)


class BrazeClientError(Exception):
    """Exception raised when Braze API requests fail."""

    def __init__(self, message: str, response: Optional[requests.Response] = None):
        super().__init__(message)
        self.response = response


class BrazeAPIClient:
    """
    Optimized API client for Braze campaign triggering.

    Example::

        client = BrazeAPIClient(api_key, api_url)
        recipient = client.build_recipient("user_id", email="user@example.com")
        response = client.send_campaign_message(
            campaign_id="campaign_id",
            recipients=[recipient],
            trigger_properties={"key": "value"}
        )
    """
    def __init__(self, api_key: str, api_url: str):
        self.api_key = api_key
        self.api_url = api_url.rstrip('/')

    def build_recipient(
        self,
        external_user_id: str,
        email: Optional[str] = None,
        send_to_existing_only: bool = False,
        attributes: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Build a recipient dict for Braze API.
        """
        recipient = {
            "external_user_id": external_user_id,
            "send_to_existing_only": send_to_existing_only
        }
        attr = attributes.copy() if attributes else {}
        if email:
            attr["email"] = email
        if attr:
            recipient["attributes"] = attr
        return recipient

    def send_campaign_message(
        self,
        campaign_id: str,
        recipients: List[Union[Dict[str, Any], str]],
        trigger_properties: Optional[Dict[str, Any]] = None,
        broadcast: bool = False
    ) -> Dict[str, Any]:
        """
        Trigger a Braze campaign for recipients.

        Args:
            campaign_id: Braze campaign ID.
            recipients: List of recipient dicts or email strings.
            trigger_properties: Personalization properties.
            broadcast: Send as broadcast.

        Returns:
            Braze API response as dict.

        Raises:
            BrazeClientError: If the API request fails.
            ValueError: If recipient format is invalid.
        """
        url = f"{self.api_url}{BrazeAPIEndpoints.SEND_CAMPAIGN}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # Build recipients list efficiently
        built_recipients = [
            r if isinstance(r, dict) else
            self.build_recipient(
                external_user_id=r,
                email=r,
                send_to_existing_only=False,
                attributes={"email": r}
            ) if isinstance(r, str) else
            (_ for _ in ()).throw(ValueError(f"Invalid recipient type: {type(r).__name__}"))
            for r in recipients
        ]

        payload = {
            "campaign_id": campaign_id,
            "trigger_properties": trigger_properties or {},
            "recipients": built_recipients,
            "broadcast": broadcast
        }

        try:
            # Log count only, not email addresses (privacy/GDPR)
            logger.info(
                "Sending Braze campaign %s to %d recipients",
                campaign_id,
                len(recipients)
            )
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            logger.info(
                "Successfully sent Braze campaign %s to %d recipients",
                campaign_id,
                len(recipients)
            )
            return response.json()
        except requests.HTTPError as e:
            error_msg = f"Braze API HTTP error: {e}"
            if e.response is not None:
                error_msg += f" - Status: {e.response.status_code}, Response: {e.response.text[:200]}"
            logger.error(error_msg)
            raise BrazeClientError(error_msg, response=e.response) from e
        except requests.RequestException as e:
            error_msg = f"Braze API request failed: {e}"
            logger.error(error_msg)
            raise BrazeClientError(error_msg) from e
