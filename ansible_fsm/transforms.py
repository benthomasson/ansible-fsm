
import yaml
from yaml import Loader, Dumper
from yaml.representer import SafeRepresenter
from collections import OrderedDict

from pprint import pprint

def dict_constructor(loader, node):
    return OrderedDict(loader.construct_pairs(node))

def dict_representer(dumper, data):
    return dumper.represent_dict(data.items())

_mapping_tag = yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG

Loader.add_constructor(_mapping_tag, dict_constructor)

Dumper.add_representer(OrderedDict, dict_representer)

Dumper.add_representer(str, SafeRepresenter.represent_str)


def designer_to_fsm(designer):
    """
    Converts schema from fsm-designer-svg.com to FSM schema.
    """
    states = [OrderedDict(name=x['label'], handlers={}) for x in sorted(designer['states'], key=lambda x: x['id'])]
    states_map = {x['name']: x for x in states}
    for t in designer['transitions']:
        from_state = states_map[t['from_state']]
        from_state['handlers'][t['label']] = [dict(change_state=t['to_state'])]
    for s in states:
        if not s['handlers']:
            del s['handlers']
    fsm = OrderedDict(name=designer['name'],
                      hosts='all',
                      gather_facts=True,
                      states=states)
    return fsm


def fsm_to_designer(fsm):
    """
    Converts FSM schema to schema from fsm-designer-svg.com.
    """
    designer = dict(states=[], transitions=[])
    transitions = designer['transitions']

    designer['states'] = [dict(label=x['name']) for x in fsm['states']]
    for state in fsm['states']:
        for handler, tasks in state.get('handlers', {}).items():
            for task in tasks:
                if 'change_state' in task:
                    transitions.append(dict(from_state=state['name'],
                                            to_state=task['change_state'],
                                            label=handler))
    return designer
