
import zmq.green as zmq
import gevent
import yaml
from .. import messages
from itertools import count
import logging

logger = logging.getLogger('ansible_fsm.connectors.zmq')


class ZMQEventChannel(object):

    def __init__(self, fsm_registry, connector_registry, configuration):
        self.fsm_registry = fsm_registry
        self.connector_registry = connector_registry
        self.context = zmq.Context.instance()
        self.socket = self.context.socket(zmq.ROUTER)
        if 'bind_port' in configuration:
            self.socket_port = configuration.get('bind_port')
            self.socket.bind('tcp://{0}:{1}'.format(configuration.get('bind_address', '127.0.0.1'),
                                                    self.socket_port))
        else:
            self.socket_port = self.socket.bind_to_random_port('tcp://{0}'.format(configuration.get('bind_address', '127.0.0.1')))
        logger.info('starting zmq_thread')
        self.zmq_thread = gevent.spawn(self.receive_messages)

    def receive_messages(self):
        message_id_seq = count()
        while True:
            logger.info('waiting on recv_multipart')
            message = self.socket.recv_multipart()
            logger.info(repr(message))
            id = message.pop(0)
            try:
                msg_type = message.pop(0).decode()
                msg_data = yaml.safe_load(message.pop(0).decode())
                logger.info(repr(msg_type))
                logger.info(repr(msg_data))
            except Exception as e:
                self.socket.send_multipart([id, b'Error'])
                logger.error(str(e))
            if not isinstance(msg_type, str):
                self.socket.send_multipart([id, 'Element 1 should be str was {}'.format(type(msg_type)).encode()])
                logger.error([id, 'Element 1 should be str was {}'.format(type(msg_type)).encode()])
                continue
            if not isinstance(msg_data, dict):
                self.socket.send_multipart([id, 'Element 2 should be a dict was {}'.format(type(msg_data)).encode()])
                logger.error([id, 'Element 2 should be a dict was {}'.format(type(msg_data)).encode()])
                continue
            to_fsm_id = msg_data.get('to_fsm_id', None)
            from_fsm_id = msg_data.get('to_fsm_id', None)
            if to_fsm_id in self.fsm_registry:
                logger.info('Sending to FSM {}'.format(to_fsm_id))
                self.fsm_registry[to_fsm_id].inbox.put((1,
                                                        next(message_id_seq),
                                                        messages.Event(from_fsm_id,
                                                                       to_fsm_id,
                                                                       msg_data['name'],
                                                                       msg_data['data'])))

                logger.info('Processed')
                self.socket.send_multipart([id, b'Processed'])
            else:
                logger.info('Not processed')
                self.socket.send_multipart([id, b'Not processed'])
            gevent.sleep(0)
