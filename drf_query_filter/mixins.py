from abc import ABC
from typing import Any


from django.db.models import Q
from rest_framework.exceptions import ErrorDetail


class Empty:
    pass


class Range(ABC):
    default_list_separator = ","

    def __init__(
        self,
        *args: Any,
        list_separator: str | None = None,
        equal: bool = False,
        allow_empty: bool = True,
        **kwargs: Any,
    ):
        self.list_separator = list_separator or self.default_list_separator
        self.equal = equal
        self.allow_empty = allow_empty
        super().__init__(*args, **kwargs)

    def get_target_fields(
        self, target_fields: list[str], equal: bool
    ) -> list[tuple[str, str]]:
        field_format = "{field}__{suffix}"

        if equal:
            greater, lesser = "gte", "lte"
        else:
            greater, lesser = "gt", "lt"

        return [
            (
                field_format.format(field=target_field, suffix=greater),
                field_format.format(field=target_field, suffix=lesser),
            )
            for target_field in target_fields
        ]

    def perform_validation(self, raw_value: str) -> tuple[list[Any], Any]:
        raw_value_list = raw_value.split(self.list_separator)

        if len(raw_value_list) < 2:
            return [ErrorDetail("Requires two values", code="not_enough_values")], None

        errors: list[Any] = []

        if raw_value_list[0]:
            left_errors, left_value = super().perform_validation(  # type: ignore
                raw_value_list[0]
            )
            errors.extend(left_errors)
        elif self.allow_empty:
            left_value = Empty()
        else:
            errors.append(ErrorDetail("Left value is empty", code="missing_left_value"))
            left_value = Empty()

        if raw_value_list[1]:
            right_errors, right_value = super().perform_validation(  # type: ignore
                raw_value_list[1]
            )
            errors.extend(right_errors)
        elif self.allow_empty:
            right_value = Empty()
        else:
            errors.append(ErrorDetail("Right value is empty", code="missing_right_value"))
            right_value = Empty()

        return errors, [left_value, right_value]

    def get_query(self, value: Any) -> Q:
        left_value, right_value = value
        query_dict = {}

        for target_field_gt, target_field_lt in self.get_target_fields(
            self.target_fields, self.equal  # type: ignore
        ):
            if not isinstance(left_value, Empty):
                query_dict[target_field_gt] = left_value
            if not isinstance(right_value, Empty):
                query_dict[target_field_lt] = right_value

        return Q(**query_dict, _connector=self.connector)  # type: ignore

    def get_schema(self) -> dict[str, Any]:
        # This is probably very wrong
        return {
            "type": "string",
            "format": r"\w,\w",
        }
