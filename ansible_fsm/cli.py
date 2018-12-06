

"""
Usage:
    ansible-fsm [options] <fsm.yml>

Options:
    -h, --help        Show this page
    --debug            Show debug logging
    --verbose        Show verbose logging
"""
from gevent import monkey
monkey.patch_all()
import gevent

from docopt import docopt
import logging
import sys
import yaml
from ansible_fsm.event import ZMQEventChannel

from ansible_fsm.parser import parse_to_ast

logger = logging.getLogger('cli')


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


    with open(parsed_args['<fsm.yml>']) as f:
        data = yaml.safe_load(f.read())

    ast = parse_to_ast(data)
    print (ast)

    event = ZMQEventChannel()
    gevent.joinall([event.zmq_thread])

    return 0

