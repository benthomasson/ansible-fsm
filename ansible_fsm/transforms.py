
import yaml
from yaml import Dumper
from yaml.representer import SafeRepresenter
from collections import OrderedDict

from pprint import pprint

def dict_representer(dumper, data):
    return dumper.represent_dict(data.items())

Dumper.add_representer(OrderedDict, dict_representer)

Dumper.add_representer(str, SafeRepresenter.represent_str)


def designer_to_fsm(designer):
    print (designer)
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
