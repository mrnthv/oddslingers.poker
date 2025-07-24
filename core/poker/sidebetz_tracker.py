import requests
from django.conf import settings

def send_gamestate_to_sidebetz(gamestate, url):
    """
    Sends the gamestate to the Sidebetz endpoint.
    """
    if not settings.SIDEBETZ_ENABLED:
        return

    try:
        requests.post(url, json=gamestate)
    except requests.exceptions.RequestException as e:
        # Log the error, but don't crash the server
        print(f"Error sending gamestate to Sidebetz: {e}")
