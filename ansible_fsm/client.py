

import zmq
from .messages import serialize


class ZMQClientChannel(object):

    def __init__(self):
        self.context = zmq.Context.instance()
        self.socket = self.context.socket(zmq.DEALER)
        self.socket.connect('tcp://127.0.0.1:5556')

    def send(self, event):
        self.socket.send_multipart(serialize(event))
        msg = self.socket.recv_multipart()
        print (msg)

    def receive(self):
        return self.socket.recv_multipart()

