

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

import logging
FORMAT = "[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s"
logging.basicConfig(filename='ansible_fsm.log', level=logging.DEBUG, format=FORMAT) # noqa

from docopt import docopt
import logging
import sys
import yaml
from ansible_fsm.event import ZMQEventChannel

from ansible_fsm.parser import parse_to_ast
from .tracer import ConsoleTraceLog
from .fsm import FSMController, State

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


    tracer = ConsoleTraceLog()

    fsms = []

    for fsm_id, fsm in enumerate(ast.fsms):
        states = {}
        for state in fsm.states:
            handlers = {}
            for handler in state.handlers:
                handlers[handler.name] = handler.body
            states[state.name] = State(state.name, handlers)
        print (states)
        if 'Start' not in states:
            raise Exception('Missing required "Start" state in FSM: "{0}"'.format(fsm.name))
        fsm_controller = FSMController(dict(),
                                       fsm.name,
                                       fsm_id,
                                       states,
                                       states.get('Start'),
                                       tracer,
                                       tracer)
        fsms.append(fsm_controller)

    fsm_threads = [x.thread for x in fsms]

    event = ZMQEventChannel(fsms)
    try:
        gevent.joinall(fsm_threads)
    finally:
        for fsm in fsms:
            fsm.shutdown()
    return 0

