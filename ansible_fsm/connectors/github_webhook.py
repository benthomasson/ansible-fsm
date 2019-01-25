

from flask import Flask, request
import gevent
import json
import hmac
from .. import messages
from itertools import count


class GitHubWebHookChannel(object):

    def __init__(self, fsm_registry, connector_registry, configuration):
        self.fsm_registry = fsm_registry
        self.connector_registry = connector_registry
        self.app = Flask(__name__)
        self.host = configuration.get('bind_address', '0.0.0.0')
        self.port = int(configuration.get('bind_port', '80'))
        self.fsm_name = configuration.get('receiving_fsm', 'FSM1')
        self.webhook_url = configuration.get('webhook_url', '/')
        self.sha1_hex_digest = configuration.get('sha1_hex_digest', None)
        self.app_thread = gevent.spawn(self.start_app)

        @self.app.route(self.webhook_url, methods=['GET', 'POST'])
        def index():
            message_id_seq = count()
            try:
                if self.sha1_hex_digest is not None:
                    hub_signature = request.headers.get('X-Hub-Signature')
                    if hub_signature is None:
                        return 'Error'
                    if not hub_signature.startswith('sha1='):
                        return 'Error'
                    hub_signature = hub_signature[len('sha1='):]
                    if not hmac.compare_digest(self.sha1_hex_digest, hub_signature):
                        return 'Error'
                if request.method == 'GET':
                    return 'OK'
                elif request.method == 'POST':
                    event_type = request.headers.get('X-GitHub-Event')
                    if self.fsm_name in self.fsm_registry:
                        self.fsm_registry[self.fsm_name].inbox.put((1,
                                                                    next(message_id_seq),
                                                                    messages.Event(None,
                                                                                   self.fsm_registry[self.fsm_name].fsm_id,
                                                                                   event_type,
                                                                                   request.json)))

                        return json.dumps({'msg': 'Processed!'})
                    else:
                        return json.dumps({'msg': 'Not Processed!'})
                else:
                    return 'ERROR'
            except BaseException as e:
                print(e)
                return 'Error'

    def start_app(self):
        self.app.run(host=self.host, port=self.port)
