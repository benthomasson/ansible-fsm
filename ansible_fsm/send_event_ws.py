
"""
Usage:
    send_event_ws [options] <fsm-id> <event-name> [<args>...]

Options:
    -h, --help        Show this page
    --debug            Show debug logging
    --verbose        Show verbose logging
"""
from docopt import docopt
import logging
import sys

from .messages import Event, json_serialize
from websocket import create_connection

logger = logging.getLogger('send_event')


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    parsed_args = docopt(__doc__, args)
    if parsed_args['--debug']:
        logging.basicConfig(level=logging.DEBUG)
    elif parsed_args['--verbose']:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)


    client = create_connection("ws://localhost:8080")
    args = dict()
    for arg in parsed_args['<args>']:
        if "=" in arg:
            key, _, value = arg.partition('=')
            if key in args:
                raise Exception("Duplicate values for '{0}' in args".format(key))
            args[key] = value
        else:
            raise Exception("Args should contain '=' between key and value")
    print(json_serialize(Event("0",
                                parsed_args['<fsm-id>'],
                                parsed_args['<event-name>'],
                                args)))
    client.send(json_serialize(Event("0",
                                parsed_args['<fsm-id>'],
                                parsed_args['<event-name>'],
                                args)))
    print(client.recv())
    client.close()


    return 0


