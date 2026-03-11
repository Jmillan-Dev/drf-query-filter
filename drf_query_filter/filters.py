import itertools
from typing import Any


from django.db.models import QuerySet
from rest_framework import filters
from rest_framework.request import Request


from . import fields


class QueryParamFilter(filters.BaseFilterBackend):
    query_param_attr = "query_params"
    query_param_call = "get_query_params"

    query_schema_attr = "query_schema"
    query_schema_call = "get_query_schema"

    query_raise_exceptions = "query_raise_exceptions"

    def get_query_fields(self, view: Any) -> list[fields.Node]:
        try:
            return getattr(view, self.query_param_call)()  # type: ignore
        except AttributeError:
            return getattr(view, self.query_param_attr, [])

    def get_query_fields_for_schema(self, view: Any) -> list[fields.Node]:
        try:
            schema = getattr(view, self.query_schema_call)()
        except AttributeError:
            schema = getattr(view, self.query_schema_attr, [])

        if not schema:
            schema = self.get_query_fields(view)

        return schema  # type: ignore

    def get_query_raise_exceptions(self, view: Any) -> bool:
        try:
            return getattr(view, self.query_raise_exceptions)  # type: ignore
        except AttributeError:
            return False

    def filter_queryset(
        self, request: Request, queryset: QuerySet, view: Any  # type: ignore
    ) -> QuerySet:  # type: ignore
        query_fields = self.get_query_fields(view)
        query_params = request.query_params

        if not query_params or not query_fields:
            return queryset

        for field in query_fields:
            queryset, _ = field.filter(
                queryset,
                query_params,
                raise_exceptions=self.get_query_raise_exceptions(view),
            )

        return queryset

    def get_schema_operation_parameters(self, view: Any) -> Any:
        query_fields = self.get_query_fields_for_schema(view) or []

        return list(
            itertools.chain.from_iterable(
                field.get_schema_operation_parameters() for field in query_fields
            )
        )
