"""
Defines and configures connectors that send events to the automata.
"""

from .zmq import ZMQEventChannel

registry = {'zmq': ZMQEventChannel}
