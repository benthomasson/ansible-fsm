

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
    gevent.joinall(fsm_threads)

    return 0

