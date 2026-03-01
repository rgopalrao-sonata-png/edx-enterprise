"""
Unit tests for BrazeAPIClient functionality and integration.
"""
import unittest
from unittest.mock import MagicMock, patch

import requests

from enterprise.api_client.braze_client import BrazeAPIClient


class TestBrazeAPIClient(unittest.TestCase):
    """
    Test cases for BrazeAPIClient methods and API interactions.
    """
    def setUp(self):
        self.api_key = 'test-key'
        self.api_url = 'https://rest.iad-06.braze.com/'
        self.client = BrazeAPIClient(self.api_key, self.api_url)

    def test_build_recipient_basic(self):
        recipient = self.client.build_recipient('user1')
        self.assertEqual(recipient['external_user_id'], 'user1')
        self.assertFalse(recipient['send_to_existing_only'])
        self.assertNotIn('attributes', recipient)

    def test_build_recipient_with_email(self):
        recipient = self.client.build_recipient('user2', email='user2@example.com')
        self.assertIn('attributes', recipient)
        self.assertEqual(recipient['attributes']['email'], 'user2@example.com')

    def test_build_recipient_with_attributes(self):
        attrs = {'foo': 'bar'}
        recipient = self.client.build_recipient('user3', attributes=attrs)
        self.assertIn('attributes', recipient)
        self.assertEqual(recipient['attributes']['foo'], 'bar')

    @patch('requests.post')
    def test_send_campaign_message_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {'result': 'ok'}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        recipients = [self.client.build_recipient('user1')]
        result = self.client.send_campaign_message(
            campaign_id='cid',
            recipients=recipients,
            trigger_properties={'foo': 'bar'},
            broadcast=True
        )
        self.assertEqual(result, {'result': 'ok'})
        mock_post.assert_called_once()

    @patch('requests.post')
    def test_send_campaign_message_failure(self, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError('HTTP error')
        mock_post.return_value = mock_response

        recipients = [self.client.build_recipient('user1')]
        with self.assertRaises(RuntimeError):
            self.client.send_campaign_message(
                campaign_id='cid',
                recipients=recipients,
                trigger_properties={'foo': 'bar'},
                broadcast=True
            )


if __name__ == '__main__':
    unittest.main()
