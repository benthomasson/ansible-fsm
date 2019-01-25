
import gevent
import json
import logging
from .. import messages

from geventwebsocket import WebSocketServer, WebSocketApplication, Resource
from collections import OrderedDict
from itertools import count

FSM_REGISTRY = dict()
CONNECTOR_REGISTRY = dict()
message_id_seq = count()

logger = logging.getLogger('ansible_fsm.connectors.websocket')


class WebSocketChannelApplication(WebSocketApplication):

    def on_open(self):
        logger.debug("connection open")

    def on_close(self, reason):
        logger.debug("connection closed")

    def on_message(self, message):
        logger.debug("message received")
        if message is None:
            return
        data = json.loads(message)
        msg_type = data.pop(0)
        msg_data = data.pop(0)
        to_fsm_id = msg_data.get('to_fsm_id', None)
        if to_fsm_id in FSM_REGISTRY:
            FSM_REGISTRY[to_fsm_id].inbox.put((1,
                                               next(message_id_seq),
                                               messages.Event(None,
                                                              FSM_REGISTRY[to_fsm_id].fsm_id,
                                                              msg_data['name'],
                                                              msg_data['data'])))

            self.ws.send('Processed')
        else:
            self.ws.send('Not Processed')


class WebSocketChannel(object):

    def __init__(self, fsm_registry, connector_registry, configuration):
        global FSM_REGISTRY, CONNECTOR_REGISTRY
        FSM_REGISTRY = fsm_registry
        CONNECTOR_REGISTRY = connector_registry
        self.fsm_registry = fsm_registry
        self.connector_registry = connector_registry
        self.bind_address = configuration.get('bind_address', '')
        self.bind_port = int(configuration.get('bind_port', '8080'))
        self.websocket_thread = gevent.spawn(self.receive_messages)

    def receive_messages(self):
        WebSocketServer((self.bind_address, self.bind_port),
                        Resource(OrderedDict([('/', WebSocketChannelApplication)]))).serve_forever()
