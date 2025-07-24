from unittest.mock import patch

from django.test import TestCase

from ..sidebetz_tracker import send_gamestate_to_sidebetz


class SidebetzTrackerTests(TestCase):

    @patch('requests.post')
    def test_send_gamestate_to_sidebetz(self, mock_post):
        """
        Test that send_gamestate_to_sidebetz sends a POST request to the correct URL with the correct data.
        """
        gamestate = {'foo': 'bar'}
        url = 'https://example.com/api/update-game-state'
        with self.settings(SIDEBETZ_ENABLED=True):
            send_gamestate_to_sidebetz(gamestate, url)

        mock_post.assert_called_once_with(url, json=gamestate)

    @patch('requests.post')
    def test_send_gamestate_to_sidebetz_disabled(self, mock_post):
        """
        Test that send_gamestate_to_sidebetz does not send a POST request when SIDEBETZ_ENABLED is False.
        """
        gamestate = {'foo': 'bar'}
        url = 'https://example.com/api/update-game-state'
        with self.settings(SIDEBETZ_ENABLED=False):
            send_gamestate_to_sidebetz(gamestate, url)

        mock_post.assert_not_called()
