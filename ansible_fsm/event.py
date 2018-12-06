
import zmq.green as zmq
import gevent
import yaml


class ZMQEventChannel(object):

    def __init__(self):
        self.context = zmq.Context.instance()
        self.socket = self.context.socket(zmq.ROUTER)
        self.socket.bind('tcp://127.0.0.1:5556')
        self.zmq_thread = gevent.spawn(self.receive_messages)
        self.fsms = dict()

    def receive_messages(self):
        while True:
            message = self.socket.recv_multipart()
            id = message.pop(0)
            msg_type = message.pop(0).decode()
            msg_data = yaml.safe_load(message.pop(0).decode())
            print (id, msg_type, msg_data)
            to_fsm_id = msg_data.get('to_fsm_id', None)
            self.socket.send_multipart([id, b'Hi'])
            gevent.sleep(0)
