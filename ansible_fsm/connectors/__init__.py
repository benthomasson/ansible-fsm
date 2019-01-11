"""
Defines and configures connectors that send events to the automata.
"""

from .zmq import ZMQEventChannel
from .websocket import WebSocketChannel
from .webhook import WebHookChannel
from .github_webhook import GitHubWebHookChannel

registry = {'zmq': ZMQEventChannel,
            'websocket': WebSocketChannel,
            'webhook': WebHookChannel,
            'github_webhook': GitHubWebHookChannel}


def register(name, connector):
    registry[name] = connector

