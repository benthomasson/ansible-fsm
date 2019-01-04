"""
Defines and configures connectors that send events to the automata.
"""

from .zmq import ZMQEventChannel
from .websocket import WebSocketChannel

registry = {'zmq': ZMQEventChannel,
            'websocket': WebSocketChannel}


def register(name, connector):
    registry[name] = connector

