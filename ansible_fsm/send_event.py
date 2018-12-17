
"""
Usage:
    send_event [options] <fsm-id> <event-name> [<args>...]

Options:
    -h, --help        Show this page
    --debug            Show debug logging
    --verbose        Show verbose logging
"""
from docopt import docopt
import logging
import sys

from ansible_fsm.client import ZMQClientChannel
from .messages import Event

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


    client = ZMQClientChannel()
    args = dict()
    for arg in parsed_args['<args>']:
        if "=" in arg:
            key, _, value = arg.partition('=')
            if key in args:
                raise Exception("Duplicate values for '{0}' in args".format(key))
            args[key] = value
        else:
            raise Exception("Args should contain '=' between key and value")
    client.send(Event("0",
                      parsed_args['<fsm-id>'],
                      parsed_args['<event-name>'],
                      args))


    return 0


