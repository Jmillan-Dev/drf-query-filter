from enum import Enum


class ConnectorType(Enum):
    AND = 'AND'
    OR = 'OR'

    @classmethod
    def has_value(cls, value: int) -> bool:
        return value in cls._value2member_map_


def print_tree(node, level=0, final=False, parent_final=False):
    # this function is for debug purposes
    if level > 0:
        tab = '%(space)s%(symbol)s── ' % {
            'space': ('%s   ' % (' ' if parent_final else '│')) * (level-1),
            'symbol': '└' if final else '├'
        }
    else:
        tab = ''

    print('%(tab)s%(connector)s %(class_name)s(%(name)s)' % {
        'tab': tab,
        'connector': node.connector.value + ':' if node.children else '',
        'class_name': node.__class__.__name__,
        'name': getattr(node, 'field_name', ''),
    })

    # print children with level
    for child in node.children:
        print_tree(child, level + 1, child is node.children[-1], final)
