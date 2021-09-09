from django.db.models import Q
from django.test import TestCase
from rest_framework.exceptions import ValidationError

from drf_query_filter import fields, filters
from drf_query_filter.utils import ConnectorType


class SimpleView:
    query_params = [
        fields.IntegerField('id') & fields.ChoicesField('state', choices=['A', 'S', 'N']),
        fields.Field('search', ['name__icontains', 'category__name'], connector=ConnectorType.OR)
    ]

    def __init__(self, raise_exceptions=False, **kwargs):
        self.query_raise_exceptions = raise_exceptions
        if 'query_params' in kwargs:
            self.query_params = kwargs.get('query_params')


class FakeQuerySet:
    def __init__(self):
        self.query = list()
        self.annotate = list()

    def annotate(self, **kwargs):
        self.annotate.append(kwargs)
        return self

    def filter(self, query):
        self.query.append(query)
        return self


class FakeRequest:
    def __init__(self, **kwargs):
        self.query_params = kwargs


class FilterTests(TestCase):

    def test_with_normal_filter(self):
        f = filters.QueryParamFilter()
        queryset = FakeQuerySet()
        view = SimpleView()
        f.filter_queryset(
            request=FakeRequest(id='10', state='A', search='simon jefa!'),
            view=view, queryset=queryset
        )
        self.assertEqual(len(queryset.query), 2)
        self.assertEqual(queryset.query[0], Q(id=10) & Q(state='A'))
        self.assertEqual(queryset.query[1], Q(name__icontains='simon jefa!') | Q(category__name='simon jefa!'))

        queryset = FakeQuerySet()
        f.filter_queryset(
            request=FakeRequest(id='28', state='None'),
            view=view, queryset=queryset
        )
        self.assertEqual(len(queryset.query), 1)
        self.assertEqual(queryset.query[0], Q(id=28))

        queryset = FakeQuerySet()
        f.filter_queryset(
            request=FakeRequest(search='sis'),
            view=view, queryset=queryset
        )
        self.assertEqual(len(queryset.query), 1)
        self.assertEqual(queryset.query[0], Q(name__icontains='sis') | Q(category__name='sis'))

    def test_with_filter_validations(self):
        f = filters.QueryParamFilter()
        queryset = FakeQuerySet()

        with self.assertRaises(ValidationError):
            f.filter_queryset(
                request=FakeRequest(id='id', state='None', search=''),
                view=SimpleView(raise_exceptions=True), queryset=queryset
            )

        with self.assertRaises(ValidationError):
            f.filter_queryset(
                request=FakeRequest(id='10', state='a'),
                view=SimpleView(raise_exceptions=True), queryset=queryset
            )

    def test_with_no_query_param_fields(self):
        f = filters.QueryParamFilter()
        queryset = FakeQuerySet()
        view = SimpleView(query_params=None)
        f.filter_queryset(request=FakeRequest(ignore=True),view=view, queryset=queryset)


