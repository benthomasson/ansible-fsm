

"""
Usage:
    ansible-fsm [options] <fsm.yml>

Options:
    -h, --help       Show this page
    --debug          Show debug logging
    --verbose        Show verbose logging
    --inventory=<i>  Use a specific inventory
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
from itertools import count
from ansible_fsm.event import ZMQEventChannel

from ansible_fsm.parser import parse_to_ast
from .tracer import ConsoleTraceLog, FileSystemTraceLog
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

    default_inventory = 'localhost ansible_connection=local'
    inventory = default_inventory
    if parsed_args['--inventory']:
        with open(parsed_args['--inventory']) as f:
            inventory = f.read()

    with open(parsed_args['<fsm.yml>']) as f:
        data = yaml.safe_load(f.read())

    fsm_registry = dict()

    ast = parse_to_ast(data)

    tracer = FileSystemTraceLog('fsm.log')

    fsms = []

    fsm_id_seq = count(0)

    for fsm in ast.fsms:
        play_header = dict(name=fsm.name,
                           hosts=fsm.hosts,
                           gather_facts=fsm.gather_facts)
        fsm_id = next(fsm_id_seq)
        states = {}
        for state in fsm.states:
            handlers = {}
            for handler in state.handlers:
                handlers[handler.name] = handler.body
            states[state.name] = State(state.name, handlers)
        if 'Start' not in states:
            raise Exception('Missing required "Start" state in FSM: "{0}"'.format(fsm.name))
        fsm_controller = FSMController(fsm.name,
                                       fsm_id,
                                       states,
                                       states.get('Start'),
                                       tracer,
                                       tracer,
                                       fsm_registry,
                                       fsm_id_seq,
                                       inventory,
                                       play_header)
        fsms.append(fsm_controller)

    fsm_threads = [x.thread for x in fsms]
    fsm_registry.update({x.name: x for x in fsms})

    for fsm in fsms:
        fsm.enter()

    event = ZMQEventChannel(fsm_registry)
    try:
        gevent.joinall(fsm_threads)
    except KeyboardInterrupt:
        print ('Caught KeyboardInterrupt shutting down...')
    finally:
        for fsm in fsms:
            fsm.shutdown()
        print ('Successful shutdown')
    return 0

