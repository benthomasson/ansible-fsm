from collections import OrderedDict

from pprint import pprint


def _merge_list_of_named_items(merged, a, b, sub_merge_fn):
    """
    Merge two lists by merging items with the same name.
    """
    a_items = {x['name']: x for x in a}
    b_items = OrderedDict()
    for item_b in b:
        b_items[item_b['name']] = item_b
    for key in b_items.keys():
        merged.append(sub_merge_fn(b_items[key], a_items.get(key, {})))
    for key in a_items.keys():
        if key in b_items:
            continue
        merged.append(a_items[key])


def _merge_ordered_dicts(merged, a, b, skip_keys=[]):
    """
    Merge two ordered dicts and preserve the order of the keys from b then add keys from a that are not in b.
    """
    for key in b.keys():
        if key in skip_keys:
            pass
        else:
            merged[key] = b[key]
    for key in a.keys():
        if key in skip_keys:
            pass
        elif key in b:
            continue
        else:
            merged[key] = a[key]

def merge_ast(a, b):
    """
    Merge two ASTs by merging FSMs with the same name.
    """
    merged = []
    _merge_list_of_named_items(merged, a, b, merge_fsm)
    return merged


def merge_fsm(a, b):
    """
    Merge two FSMs and preserve the order of the keys from b then add keys from a that are not in b.
    """
    merged = OrderedDict()
    _merge_ordered_dicts(merged, a, b, skip_keys=['states'])
    merged['states'] = []
    _merge_list_of_named_items(merged['states'], a.get('states', []), b.get('states', []), merge_state)
    return merged


def merge_state(a, b):
    merged = OrderedDict()
    _merge_ordered_dicts(merged, a, b, skip_keys=['handlers'])
    merged['handlers'] = {}
    _merge_ordered_dicts(merged['handlers'], a.get('handlers', {}), b.get('handlers', {}))
    return merged
