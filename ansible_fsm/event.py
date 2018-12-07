
import zmq.green as zmq
import gevent
import yaml
from . import messages


class ZMQEventChannel(object):

    def __init__(self, fsms):
        self.context = zmq.Context.instance()
        self.socket = self.context.socket(zmq.ROUTER)
        self.socket.bind('tcp://127.0.0.1:5556')
        self.zmq_thread = gevent.spawn(self.receive_messages)
        self.fsms = {x.name: x for x in fsms}

    def receive_messages(self):
        while True:
            message = self.socket.recv_multipart()
            id = message.pop(0)
            msg_type = message.pop(0).decode()
            msg_data = yaml.safe_load(message.pop(0).decode())
            print (id, msg_type, msg_data)
            to_fsm_id = msg_data.get('to_fsm_id', None)
            self.fsms[to_fsm_id].inbox.put(messages.Event(None,
                                                          self.fsms[to_fsm_id].fsm_id,
                                                          msg_data['name'],
                                                          msg_data['args']))

            self.socket.send_multipart([id, b'Processed'])
            gevent.sleep(0)
