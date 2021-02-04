from typing import List

from rest_framework import filters
from rest_framework.exceptions import ValidationError

from drf_query_filter import fields


class QueryParamFilter(filters.BaseFilterBackend):
    # Defaults:
    raise_exceptions = False
    
    # Look ups for attrs in view
    query_param_attr = 'query_params'
    query_param_call = 'get_query_params'
    query_raise_exceptions = 'query_raise_exceptions'
    
    def get_raise_exceptions(self, view) -> bool:
        return getattr(view, self.query_raise_exceptions, None) or self.raise_exceptions
    
    def get_query_params(self, view) -> List[fields.Node]:
        get_query_params = getattr(view, self.query_param_call, None)
        if callable(get_query_params):
            return get_query_params()
        else:
            return getattr(view, self.query_param_attr, None)
        
    def filter_queryset(self, request, queryset, view):
        query_fields = self.get_query_params(view)
        errors = {}
        query_params = request.query_params
        if not query_params:
            return queryset
            
        for field in query_fields:
            queryset, field_errors = field.filter(queryset, request.query_params, self.get_raise_exceptions(view))
            if field_errors:
                errors.update(field_errors)
        if errors and self.get_raise_exceptions(view):
            raise ValidationError(errors)
        return queryset
