"""
Braze API client for campaign triggering and campaign management.
Provides methods to build recipients and send campaign messages to Braze.
"""
import logging
from typing import Any, Dict, List, Optional

import requests
from braze.constants import BrazeAPIEndpoints

logger = logging.getLogger(__name__)


class BrazeAPIClient:
    """
    Optimized API client for Braze campaign triggering.

    Example:
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
        recipients: List[Dict[str, Any]],
        trigger_properties: Optional[Dict[str, Any]] = None,
        broadcast: bool = False
    ) -> Dict[str, Any]:
        """
        Trigger a Braze campaign for recipients.

        Args:
            campaign_id: Braze campaign ID.
            recipients: List of recipient dicts.
            trigger_properties: Personalization properties.
            broadcast: Send as broadcast.

        Returns:
            Braze API response as dict.
        """
        url = f"{self.api_url}{BrazeAPIEndpoints.SEND_CAMPAIGN}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        # Build recipients as required: [{external_user_id, send_to_existing_only, attributes: {email}}]
        built_recipients = []
        for r in recipients:
            if isinstance(r, dict):
                built_recipients.append(r)
            elif isinstance(r, str):
                built_recipients.append(self.build_recipient(
                    external_user_id=r,
                    email=r,
                    send_to_existing_only=False,
                    attributes={"email": r}
                ))
            else:
                raise ValueError("Recipient must be dict or str (email)")
        payload = {
            "campaign_id": campaign_id,
            "trigger_properties": trigger_properties or {},
            "recipients": built_recipients,
            "broadcast": broadcast
        }
        try:
            logger.info(f"Sending Braze campaign message to {len(recipients)} recipients ")
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise RuntimeError(f"Braze API request failed: {e}") from e
