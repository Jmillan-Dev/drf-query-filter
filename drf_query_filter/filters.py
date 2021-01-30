from typing import List, Union, Tuple, Dict

from django.db.models import Q
from rest_framework import filters
from rest_framework.exceptions import ValidationError

from drf_query_filter import utils
from drf_query_filter import fields


class QueryParamFilter(filters.BaseFilterBackend):
    """
    This is a complex filter for the project.
    """
    
    # Defaults:
    raise_exceptions = False
    query_type = utils.QueryType.AND
    
    # Look ups for attrs in view
    query_type_attr = 'query_type'
    query_param_attr = 'query_params'
    query_param_func = 'get_query_params'
    query_raise_exceptions = 'query_raise_exceptions'
    
    def get_raise_exceptions(self, view) -> bool:
        return getattr(view, self.query_raise_exceptions, None) or self.raise_exceptions
    
    def get_query_default_type(self, view):
        return getattr(view, self.query_type_attr, None) or self.query_type
    
    def get_query_params(self, view) -> List[Union[fields.Field, int]]:
        get_query_params = getattr(view, self.query_param_func, None)
        if callable(get_query_params):
            return get_query_params()
        else:
            return getattr(view, self.query_param_attr, None)
    
    def process_query(self, request, view) -> Tuple[Q, Dict]:
        """ Check all of them """
        query_params = self.get_query_params(view)
        query_type = self.get_query_default_type(view)
        errors = {}
        
        query = Q()
        annotate = {}
        for query_param in query_params:
            if isinstance(query_param, fields.Field):
                if query_param(request.query_params):
                    if query_param.is_valid():
                        annotate.update(query_param.get_annotate())
                        if query_type == utils.QueryType.AND:
                            query &= query_param.get_query()
                        elif query_type == utils.QueryType.OR:
                            query |= query_param.get_query()
                    else:
                        # gather all the errors found
                        errors[query_param.field_name] = ValidationError(query_param.errors).detail
            else:
                assert utils.QueryType.has_value(query_param), (
                        'given value `%s` is not a valid option, use: %s' %
                        (query_param, [item.value for item in utils.QueryType])
                )
                query_type = query_param
        
        if len(errors) > 0 and self.get_raise_exceptions(view):
            # throw the exception to be handle outside.
            raise ValidationError(errors)
        
        return query, annotate
    
    def filter_queryset(self, request, queryset, view):
        query, annotate = self.process_query(request, view)
        if annotate:
            queryset = queryset.annotate(**annotate)
        return queryset.filter(query)
