import itertools
from typing import List

from rest_framework import filters
from rest_framework.compat import coreapi, coreschema
from rest_framework.exceptions import ValidationError

from drf_query_filter import fields


def _call_or_attr(view, call, attr):
    call = getattr(view, call, None)
    if callable(call):
        return call()
    else:
        return getattr(view, attr, None)


class QueryParamFilter(filters.BaseFilterBackend):
    # Defaults:
    raise_exceptions = False

    # Look ups for attrs and functions in the view
    query_param_attr = 'query_params'
    query_param_call = 'get_query_params'

    query_schema_attr = 'query_schema'
    query_schema_call = 'get_query_schema'

    query_raise_exceptions = 'query_raise_exceptions'

    def get_raise_exceptions(self, view) -> bool:
        return getattr(view, self.query_raise_exceptions, None) or self.raise_exceptions

    def get_query_params(self, view) -> List[fields.Node]:
        return _call_or_attr(view, self.query_param_call, self.query_param_attr)

    def get_query_schema(self, view) -> List[fields.Node]:
        schema = _call_or_attr(view, self.query_schema_call,
                               self.query_schema_attr)
        if not schema:
            # Try with the default get_query_params instead
            schema = self.get_query_params(view)
        return schema

    def filter_queryset(self, request, queryset, view):
        query_fields = self.get_query_params(view)
        errors = {}
        query_params = request.query_params
        if not query_params:
            return queryset

        if not query_fields:  # do nothing if no fields are found
            return queryset

        for field in query_fields:
            queryset, field_errors = field.filter(queryset, request.query_params,
                                                  self.get_raise_exceptions(view))
            if field_errors:
                errors.update(field_errors)
        if errors and self.get_raise_exceptions(view):
            raise ValidationError(errors)
        return queryset

    def get_schema_fields(self, view):
        assert coreapi is not None, 'coreapi must be installed to use ' \
                                    '`get_schema_fields()` '
        assert coreschema is not None, 'coreschema must be installed to use ' \
                                       '`get_schema_fields()` '

        query_fields = self.get_query_schema(view) or list()

        return list(itertools.chain.from_iterable(
            field.get_coreapi_fields() for field in query_fields
        ))

    def get_schema_operation_parameters(self, view):
        query_fields = self.get_query_schema(view) or list()

        return list(itertools.chain.from_iterable(
            field.get_schema_operation_parameters() for field in query_fields
        ))
