from django.db.models import Q
from django.test import TestCase

from drf_query_filter.fields import Field
from drf_query_filter.utils import ConnectorType as Con


class NodeTests(TestCase):

    def test_node_behaviour(self):
        node = Field('a') & Field('b') & Field('c')
        self.assertEqual(repr(node), '(AND: [a, b, c])')

        node = Field('a') & Field('b') | Field('c')
        self.assertEqual(repr(node), '(OR: [(AND: [a, b]), c])')

        node = Field('a') | Field('b') & Field('c')
        self.assertEqual(repr(node), '(OR: [a, (AND: [b, c])])')

        node = Field('a') | Field('b') & Field('c') | Field('d')
        self.assertEqual(repr(node), '(OR: [a, (AND: [b, c]), d])')

        node = (Field('a') | Field('b')) & (Field('c') | Field('d'))
        self.assertEqual(repr(node), '(AND: [(OR: [a, b]), (OR: [c, d])])')

    def test_complete_query_generation(self):
        node = Field('a') & Field('b')
        query, _ = node.get_filter({'a': 'value', 'b': 'value'})
        self.assertEqual(query, Q(a='value') & Q(b='value'))

        node = Field('a') | Field('b')
        query, _ = node.get_filter({'a': 'value', 'b': 'value'})
        self.assertEqual(query, Q(a='value') | Q(b='value'))

        node = Field('a', ['a_a', 'a_b'], connector=Con.OR) & Field('b')
        query, _ = node.get_filter({'a': 'value_a', 'b': 'value_b'})
        self.assertEqual(query, Q(a_a='value_a', a_b='value_a',
                                  _connector='OR') & Q(b='value_b'))

    def test_partial_query_generation(self):
        node = Field('a') & Field('b')
        query, _ = node.get_filter({'a': 'value'})
        self.assertEqual(query, Q(a='value'))

        node = Field('a') | Field('b') & Field('c')
        query, _ = node.get_filter({'a': 'value', 'c': 'value'})
        self.assertEqual(query, Q(a='value') | Q(c='value'))
        query, _ = node.get_filter({'b': 'value', 'c': 'value'})
        self.assertEqual(query, Q(b='value') & Q(c='value'))
        query, _ = node.get_filter({'a': 'value', 'b': 'value'})
        self.assertEqual(query, Q(a='value') | Q(b='value'))

        node = (Field('a') | Field('b')) & Field('c')
        query, _ = node.get_filter({'a': 'value', 'c': 'value'})
        self.assertEqual(query, Q(a='value') & Q(c='value'))
