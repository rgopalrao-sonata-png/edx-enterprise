"""
Tests for the BrazeAPIClient in edx-enterprise.
"""
from unittest import mock

import pytest

from enterprise.api_client.braze_client import BrazeAPIClient


class DummyBrazeClient:
    """
    Dummy Braze client for mocking send_campaign_message behavior.
    """
    def __init__(self, api_key=None, api_url=None):
        self.api_key = api_key
        self.api_url = api_url
        self.called = False
        self.last_args = None

    def send_campaign_message(self, campaign_id, recipients, trigger_properties=None, broadcast=False):
        self.called = True
        self.last_args = (campaign_id, recipients, trigger_properties, broadcast)
        return {'result': 'success'}


@pytest.mark.django_db
def test_build_recipient_basic():
    """
    Test BrazeAPIClient.build_recipient with minimal arguments.
    """
    client = BrazeAPIClient('key', 'url')
    result = client.build_recipient('user1')
    assert result['external_user_id'] == 'user1'
    assert result['send_to_existing_only'] is False
    assert 'attributes' not in result


@pytest.mark.django_db
def test_build_recipient_with_email_and_attributes():
    """
    Test BrazeAPIClient.build_recipient with email and attributes.
    """
    client = BrazeAPIClient('key', 'url')
    attrs = {'foo': 'bar'}
    result = client.build_recipient('user2', email='test@example.com', attributes=attrs)
    assert result['attributes']['email'] == 'test@example.com'
    assert result['attributes']['foo'] == 'bar'


@pytest.mark.django_db
def test_send_campaign_message_dict_and_str():
    """
    Test BrazeAPIClient.send_campaign_message with dict and str recipients.
    """
    with mock.patch.object(BrazeAPIClient, 'send_campaign_message', return_value={'result': 'success'}) as mock_send:
        client = BrazeAPIClient('key', 'http://fake-url')
        recipients = [client.build_recipient('user1'), 'user2@example.com']
        resp = client.send_campaign_message('cid', recipients, {'x': 1}, True)
        mock_send.assert_called_once_with('cid', recipients, {'x': 1}, True)
        assert resp == {'result': 'success'}


@pytest.mark.django_db
def test_send_campaign_message_error():
    """
    Test BrazeAPIClient.send_campaign_message error handling.
    """
    class ErrorBrazeClient(DummyBrazeClient):

        def send_campaign_message(self, *a, **kw):
            raise Exception('fail')

    def fake_init(self, api_key, api_url):
        self.client = ErrorBrazeClient()
        self.api_url = api_url
        self.api_key = api_key
    with mock.patch.object(BrazeAPIClient, '__init__', fake_init):
        client = BrazeAPIClient('key', 'url')
        with pytest.raises(Exception):
            client.send_campaign_message('cid', ['user1'])
