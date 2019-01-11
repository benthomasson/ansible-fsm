

from flask import Flask, request
import gevent
import json


class WebHookChannel(object):

    def __init__(self, fsm_registry, configuration):
        self.app = Flask(__name__)
        self.host = configuration.get('bind_address', '0.0.0.0')
        self.port = int(configuration.get('bind_port', '80'))
        self.fsm_name = configuration.get('receiving_fsm', 'FSM1')
        self.webhook_url = configuration.get('webhook_url', '/')
        self.app_thread = gevent.spawn(self.start_app)

        @self.app.route(self.webhook_url, methods=['GET', 'POST'])
        def index():
            if request.method == 'GET':
                return 'OK'
            elif request.method == 'POST':
                return json.dumps({'msg': 'Hi!'})
            else:
                return 'ERROR'

    def start_app(self):
        self.app.run(host=self.host, port=self.port)
