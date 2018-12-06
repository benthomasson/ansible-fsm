
from collections import namedtuple
import yaml


def serialize(message):
    return [message.__class__.__name__.encode(), yaml.dump(dict(message._asdict())).encode()]

Event = namedtuple('Event', ['from_fsm_id', 'to_fsm_id', 'name', 'args'])
