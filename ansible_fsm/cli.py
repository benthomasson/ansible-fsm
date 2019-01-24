

"""
Usage:
    ansible-fsm [options] run <fsm.yml> [<uuid>]
    ansible-fsm [options] install <uuid> <output>
    ansible-fsm [options] diff <fsm.yml> <uuid>
    ansible-fsm [options] merge <fsm.yml> <uuid> [<output>]
    ansible-fsm [options] push <fsm.yml> [<uuid>]

Options:
    -h, --help       Show this page
    --debug          Show debug logging
    --verbose        Show verbose logging
    --inventory=<i>  Use a specific inventory
    --connectors=<c> Connectors file (YAML)
"""

from gevent import monkey
monkey.patch_all(thread=False)
import gevent
import shutil

import logging
FORMAT = "[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s"
logging.basicConfig(filename='ansible_fsm.log', level=logging.DEBUG, format=FORMAT)  # noqa

from docopt import docopt
import logging
import sys
import yaml
import requests
from itertools import count
from ansible_fsm.connectors import registry as connectors_registry

from ansible_fsm.parser import parse_to_ast, parse_to_fsm
from ansible_fsm.ast import FSM
from .tracer import FileSystemTraceLog
from .fsm import FSMController, State
from .transforms import designer_to_fsm, Dumper, fsm_to_designer, Loader
from .conf import settings
from .merge import merge_ast
from gevent_fsm.tools.fsm_diff import fsm_diff

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

    if parsed_args['run']:
        return ansible_fsm_run(parsed_args)
    elif parsed_args['install']:
        return ansible_fsm_install(parsed_args)
    elif parsed_args['merge']:
        return ansible_fsm_merge(parsed_args)
    elif parsed_args['push']:
        return ansible_fsm_push(parsed_args)
    elif parsed_args['diff']:
        return ansible_fsm_diff(parsed_args)
    else:
        assert False, 'Update the docopt'


def ansible_fsm_diff(parsed_args):

    response = requests.get(settings.download_server_url + parsed_args['<uuid>'])
    if response.status_code != requests.codes.ok:
        print("No such FSM found")
        return 1
    designed_fsm = yaml.safe_load(response.text)

    with open(parsed_args['<fsm.yml>']) as f:
        implementation_fsm = yaml.safe_load(f.read())

    diff = fsm_diff(designed_fsm,
                    fsm_to_designer(implementation_fsm[0]),
                    parsed_args['<uuid>'],
                    parsed_args['<fsm.yml>'],
                    silent=False)

    if diff['states'] or diff['transitions']:
        return 1
    return 0


def ansible_fsm_push(parsed_args):

    with open(parsed_args['<fsm.yml>']) as f:
        implementation_fsm = yaml.safe_load(f.read())

    files = {'file': ('fsm.yml', yaml.dump(fsm_to_designer(implementation_fsm[0])))}

    data = {}
    if parsed_args['<uuid>']:
        data['diagram_id'] = parsed_args['<uuid>']

    response = requests.post(settings.upload_server_url, files=files, data=data)
    print(response.text)
    return 0


def ansible_fsm_merge(parsed_args):

    if ansible_fsm_diff(parsed_args) == 0:
        print('No changes')
        if parsed_args['<output>']:
            print('Wrote {}'.format(parsed_args['<output>']))
            shutil.copy(parsed_args['<fsm.yml>'], parsed_args['<output>'])
        return 0

    response = requests.get(settings.download_server_url + parsed_args['<uuid>'])
    if response.status_code != requests.codes.ok:
        print("No such FSM found")
        return 1

    design = [designer_to_fsm(yaml.safe_load(response.text))]

    with open(parsed_args['<fsm.yml>']) as f:
        implementation = yaml.load(f.read(), Loader=Loader)

    merged = merge_ast(design, implementation)

    print('Writing {}'.format(parsed_args['<output>'] or parsed_args['<fsm.yml>']))
    with open(parsed_args['<output>'] or parsed_args['<fsm.yml>'], 'w') as f:
        f.write(yaml.dump(merged,
                          Dumper=Dumper,
                          default_flow_style=False))

    return 0


def ansible_fsm_install(parsed_args):

    response = requests.get(settings.server_url + parsed_args['<uuid>'])
    if response.status_code != requests.codes.ok:
        print("No such FSM found")
        return 1

    with open(parsed_args['<output>'], 'w') as f:
        f.write(yaml.dump([designer_to_fsm(yaml.safe_load(response.text))],
                          Dumper=Dumper,
                          default_flow_style=False))
    return 0


def ansible_fsm_run(parsed_args):

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
        if fsm.import_from is not None:
            with open(fsm.import_from) as f:
                data = yaml.safe_load(f.read())
                imported_fsm = parse_to_fsm(data)
                fsm = FSM(fsm.name or imported_fsm.name,
                          fsm.hosts or imported_fsm.hosts,
                          fsm.gather_facts if fsm.gather_facts is not None else imported_fsm.gather_facts,
                          fsm.roles or imported_fsm.roles,
                          fsm.states or imported_fsm.states,
                          None)
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

    connectors = []
    if parsed_args['--connectors']:
        with open(parsed_args['--connectors']) as f:
            connectors_spec = yaml.safe_load(f.read())
        if connectors_spec is None:
            pass
        elif not isinstance(connectors_spec, list):
            raise Exception('Connectors file should contain a list of connector specs')
        else:
            for connector_spec in connectors_spec:
                if 'name' not in connector_spec:
                    raise Exception('Connector spec should contain a \'name\' field')
                if connector_spec['name'] not in connectors_registry:
                    raise Exception('Could not find the {0} connector'.format(connector_spec['name']))
                connectors.append(connectors_registry[connector_spec['name']](fsm_registry, connector_spec))

    for fsm in fsms:
        fsm.enter()

    try:
        gevent.joinall(fsm_threads)
    except KeyboardInterrupt:
        print('Caught KeyboardInterrupt')
    finally:
        print('Shutting down...')
        for fsm in fsms:
            fsm.shutdown()
        print('Successful shutdown')
    return 0
