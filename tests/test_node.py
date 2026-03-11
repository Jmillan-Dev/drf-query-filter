from django.db.models import Q
from django.test import TestCase


from drf_query_filter.fields import Field


class NodeTests(TestCase):
    def test_complete_query_generation(self) -> None:
        node = Field("a") & Field("b")
        query, _, _ = node.get_filter({"a": "value", "b": "value"})
        self.assertEqual(query, Q(a="value") & Q(b="value"))

        node = Field("a") | Field("b")
        query, _, _ = node.get_filter({"a": "value", "b": "value"})
        self.assertEqual(query, Q(a="value") | Q(b="value"))

        node = Field("a", ["a_a", "a_b"], connector=Q.OR) & Field("b")
        query, _, _ = node.get_filter({"a": "value_a", "b": "value_b"})
        self.assertEqual(
            query,
            Q(a_a="value_a", a_b="value_a", _connector="OR") & Q(b="value_b"),
        )

    def test_partial_query_generation(self) -> None:
        node = Field("a") & Field("b")
        query, _, _ = node.get_filter({"a": "value"})
        self.assertEqual(query, Q(a="value"))

        node = Field("a") | Field("b") & Field("c")
        query, _, _ = node.get_filter({"a": "value", "c": "value"})
        self.assertEqual(query, Q(a="value") | Q(c="value"))
        query, _, _ = node.get_filter({"b": "value", "c": "value"})
        self.assertEqual(query, Q(b="value") & Q(c="value"))
        query, _, _ = node.get_filter({"a": "value", "b": "value"})
        self.assertEqual(query, Q(a="value") | Q(b="value"))

        node = (Field("a") | Field("b")) & Field("c")
        query, _, _ = node.get_filter({"a": "value", "c": "value"})
        self.assertEqual(query, Q(a="value") & Q(c="value"))
