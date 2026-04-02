import datetime
import decimal
import itertools
import logging
from collections.abc import Callable
from typing import Any


from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import QuerySet
from django.db.models.enums import Choices
from django.db.models.fields import (
    CharField as DjangoCharField,
    Field as DjangoField,
)
from django.db.models.functions import Concat
from django.db.models.query_utils import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import (
    ErrorDetail,
    ValidationError,
)
from rest_framework.fields import (
    flatten_choices_dict,
    get_error_detail,
    to_choices_dict,
)


from .mixins import Range

__all__ = [
    "Field",
    "ListField",
    "StringField",
    "IntegerField",
    "FloatField",
    "DecimalField",
    "DateTimeField",
    "DateField",
    "ChoicesField",
    "BooleanField",
    "ExistsField",
    "ConcatField",
    "RangeIntegerField",
    "RangeFloatField",
    "RangeDecimalField",
    "RangeDateTimeField",
    "RangeDateField",
    "InIntegerField",
    "InChoicesField",
]

log = logging.getLogger("drf_query_filter")


class Node:
    internal_error_messages: dict[str, str] = {
        "value_error": "cannot perform the operation with the given instance"
    }

    def __init__(
        self,
        childrens: list["Node"],
        connector: str = Q.AND,
    ) -> None:
        self.childrens = childrens or list()
        self.connector = connector

    def __and__(self, other: "Node") -> "Node":
        if not isinstance(other, Node):
            raise ValueError(self.internal_error_messages["value_error"])

        if self.connector == Q.AND:
            self.childrens.append(other)
            return self
        else:
            node = Node(childrens=[self, other], connector=Q.AND)
            return node

    def __or__(self, other: "Node") -> "Node":
        if not isinstance(other, Node):
            raise ValueError(self.internal_error_messages["value_error"])

        if self.connector == Q.OR:
            self.childrens.append(other)
            return self
        else:
            node = Node(childrens=[self, other], connector=Q.OR)
            return node

    def __xor__(self, other: "Node") -> "Node":
        if not isinstance(other, Node):
            raise ValueError(self.internal_error_messages["value_error"])

        if self.connector == Q.XOR:
            self.childrens.append(other)
            return self
        else:
            node = Node(childrens=[self, other], connector=Q.XOR)
            return node

    def __repr__(self) -> str:
        if self.childrens:
            return "{connector}({children})".format(
                connector=self.connector,
                children=", ".join([repr(child) for child in self.childrens]),
            )
        return "`EMPTY NODE`"

    @property
    def errors(self) -> dict[str, list[str]]:
        errors = {}
        for child in self.childrens:
            errors.update(child.errors)
        return errors

    def get_filter(
        self, data: dict[str, str]
    ) -> tuple[Q, dict[str, str], dict[str, list[Any]]]:
        annotate = {}
        errors: dict[str, list[Any]] = {}
        query = Q(_connector=self.connector)

        for child in self.childrens:
            child_query, child_annotate, child_errors = child.get_filter(data)

            if child_errors:
                errors.update(errors)

            annotate.update(child_annotate)
            if self.connector == Q.AND:
                query &= child_query
            elif self.connector == Q.OR:
                query |= child_query
            elif self.connector == Q.XOR:
                query ^= child_query

        return query, annotate, errors

    def filter(
        self,
        queryset: QuerySet,  # type: ignore
        data: dict[str, str],
        raise_exceptions: bool = False,
    ) -> tuple[QuerySet, dict[str, Any]]:  # type: ignore
        query, annotate, errors = self.get_filter(data)

        if errors and raise_exceptions:
            raise ValidationError(errors)

        if annotate:
            queryset = queryset.alias(**annotate)
        if query:
            queryset = queryset.filter(query)

        return queryset, errors

    def get_schema_operation_parameters(self) -> list[dict[str, Any]]:
        schema = list(
            itertools.chain.from_iterable(
                child.get_schema_operation_parameters() for child in self.childrens
            )
        )

        return schema


class Field(Node):
    """
    This is a Base class for all Field related to the filter.

    Initizalization of the class is to define the behaviour of the field.
    Use get_filter to process the incoming query_params dictionary and
     obtain a Q object
    """

    def __init__(
        self,
        query_param_name: str,
        target_fields: str | tuple[str, ...] | list[str] | None = None,
        validators: list[Callable[[Any], None]] | None = None,
        description: str = "",
        example: str = "",
        connector: str = Q.AND,
    ) -> None:
        """
        :param query_param_name: The name in the query params of the url.
        :param target_fields: The target fields in the queryset, This can be a
        string or a iterable of strings.
        :param validators: List of validators to validate against
        :param description: Description used in schema definition.
        :param example: Example
        :param connector: Type of connector in the target fields.
        """
        self.query_param_name = query_param_name

        assert self.query_param_name, "{}.query_param_name cannot be empty.".format(
            self.__class__.__name__
        )

        self.target_fields = target_fields or self.query_param_name

        assert isinstance(
            self.target_fields, (str, list, tuple)
        ), "given target_fields is a `{}`," "expected a str or a list/tuple.".format(
            type(self.target_fields)
        )

        if isinstance(self.target_fields, str):
            self.target_fields = [self.target_fields]

        self.validators = validators or []
        self.description = description
        self.example = example

        super().__init__(childrens=[], connector=connector)

    def __str__(self) -> str:
        if self.childrens:
            return "{query_param} {connector} {childrens}".format(
                query_param=self.query_param_name,
                connector=self.connector,
                childrens=" {} ".format(self.connector).join(
                    (repr(child) if not child.childrens else "({:r})".format(child))
                    for child in self.childrens
                ),
            )
        return self.query_param_name

    def __repr__(self) -> str:
        return ("{class_name}(query_param={query_param}, childrens={childrens})").format(
            class_name=self.__class__.__name__,
            query_param=self.query_param_name,
            childrens=", ".join(repr(children) for children in self.childrens),
        )

    def validate(self, raw_value: str) -> Any:
        """
        Function for custom validations, if there is any error it should throw
        a ValidationError Exception.
        This can also manipulate the value if required.
        """
        return raw_value

    def perform_validation(self, raw_value: str) -> tuple[list[Any], Any]:
        """This runs the validators like the fields in rest_framework"""
        errors: list[Any] = []
        value = None

        try:
            value = self.validate(raw_value)

            for validator in self.validators:
                validator(value)
        except ValidationError as exc:
            if isinstance(exc.detail, list):
                errors.extend(exc.detail)
            else:
                errors.append(exc.detail)
        except DjangoValidationError as exc:
            detail = get_error_detail(exc)
            if isinstance(detail, list):
                errors.extend(detail)
            else:
                errors.append(detail)

        return errors, value

    def get_raw_value_from_query_param(
        self, query_param_data: dict[str, str]
    ) -> tuple[bool, Any]:
        try:
            return True, query_param_data[self.query_param_name]
        except KeyError:
            return False, None

    def get_annotate(self) -> dict[str, Any]:
        """
        This should be overwritten if the field requires to annotate custom
        fields in the query
        """
        return {}

    def get_query(self, value: Any) -> Q:
        return Q(
            **{field: value for field in self.target_fields},
            _connector=self.connector,
        )

    def get_filter(
        self, query_param_data: dict[str, str]
    ) -> tuple[Q, dict[str, str], dict[str, list[Any]]]:
        found, raw_value = self.get_raw_value_from_query_param(query_param_data)
        errors = {}
        annotate = {}
        query = Q(_connector=self.connector)

        if found:
            self_errors, value = self.perform_validation(raw_value)

            if not self_errors:
                query = self.get_query(value)
                annotate = self.get_annotate()
            else:
                errors = {self.query_param_name: self_errors}

        for child in self.childrens:
            child_query, child_annotate, child_errors = child.get_filter(query_param_data)
            if child_errors:
                errors.update(child_errors)
            else:
                annotate.update(child_annotate)
                if self.connector == Q.AND:
                    query &= child_query
                elif self.connector == Q.OR:
                    query |= child_query
                elif self.connector == Q.XOR:
                    query ^= child_query

        return query, annotate, errors

    def get_schema(self) -> dict[str, Any]:
        return {"type": "string"}

    def get_schema_operation_parameter(self) -> dict[str, Any]:
        return {
            "name": self.query_param_name,
            "required": False,
            "in": "query",
            "description": self.description,
            "example": self.example,
            "schema": self.get_schema(),
        }

    def get_schema_operation_parameters(self) -> list[dict[str, Any]]:
        schema: list[dict[str, Any]] = [self.get_schema_operation_parameter()]

        if self.childrens:
            schema.extend(
                itertools.chain.from_iterable(
                    child.get_schema_operation_parameters() for child in self.childrens
                )
            )

        return schema


class ListField(Field):
    """
    ListField executes
    """

    def __init__(
        self,
        field: Field,
    ) -> None:
        self.field = field

        self.query_param_name = self.field.query_param_name
        self.description = self.field.description
        self.example = self.field.example

        if self.field.childrens:
            log.warning("Given field has childrens")

        super().__init__(
            self.field.query_param_name,
            self.field.target_fields,
            self.field.validators,
            self.field.description,
            self.field.example,
            self.field.connector,
        )

    def perform_validation(self, raw_value: str) -> tuple[list[Any], Any]:
        raw_values = raw_value.split(",")

        validated_values = []
        errors: list[Any] = []

        for raw_val in raw_values:
            if raw_val:
                field_errors, value = self.field.perform_validation(raw_val)

                if field_errors:
                    errors.extend(field_errors)
                else:
                    validated_values.append(value)

        if not validated_values:
            errors.append(
                ErrorDetail("No values has been passed", code="no_values_given")
            )

        return errors, validated_values

    def get_query(self, value: list[Any]) -> Q:
        return Q(
            **{field: value for field in self.target_fields},
            _connector=self.connector,
        )

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "array",
            "items": self.field.get_schema(),
        }

    def get_schema_operation_parameter(self) -> dict[str, Any]:
        return {
            "name": self.query_param_name,
            "required": False,
            "in": "query",
            "description": self.description,
            "example": self.example,
            "schema": self.get_schema(),
            "style": "form",
        }


class StringField(Field):
    def __init__(
        self,
        query_param_name: str,
        target_fields: str | tuple[str, ...] | list[str] | None = None,
        validators: list[Callable[[Any], None]] | None = None,
        description: str = "",
        example: str = "",
        schema_format: str = "",
        connector: str = Q.AND,
    ) -> None:
        super().__init__(
            query_param_name,
            target_fields,
            validators,
            description,
            example,
            connector,
        )
        self.schema_format = schema_format

    def validate(self, value: str) -> Any:
        return value

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "string",
            "format": self.schema_format,
        }


class IntegerField(Field):
    """
    Field that only accepts integers as values
    """

    error_messages = {
        "invalid": _("`{value}` value must be an integer."),
    }

    def validate(self, value: str) -> Any:
        try:
            return int(value)
        except (TypeError, ValueError):
            raise ValidationError(
                self.error_messages["invalid"].format(value=value),
                code="invalid",
            )

    def get_schema(self) -> dict[str, str]:
        return {
            "type": "number",
            "format": "int",
        }


class FloatField(Field):
    """
    Field that only accepts floats values
    """

    error_messages = {
        "invalid": _("`{value}` value must be a float."),
    }

    def validate(self, value: str) -> Any:
        try:
            return float(value)
        except (TypeError, ValueError):
            raise ValidationError(
                self.error_messages["invalid"].format(value=value),
                code="invalid",
            )

    def get_schema(self) -> dict[str, str]:
        return {
            "type": "number",
            "format": "float",
        }


class DecimalField(Field):
    """
    Field that only accepts Decimal values
    """

    error_messages = {
        "invalid": _("`{value}` value must be a double."),
        "is_nan": _("`{value}` value must not be NaN"),
        "is_inf": _("`{value}` value must not be Infinite"),
    }

    def validate(self, value: str) -> Any:
        try:
            value_decimal = decimal.Decimal(value)
        except (decimal.InvalidOperation, TypeError, ValueError):
            raise ValidationError(
                self.error_messages["invalid"].format(value=value),
                code="invalid",
            )

        if value_decimal.is_nan():
            raise ValidationError(
                self.error_messages["is_nan"].format(value=value), code="is_nan"
            )

        if value_decimal in (decimal.Decimal("Inf"), decimal.Decimal("-Inf")):
            raise ValidationError(
                self.error_messages["is_inf"].format(value=value), code="is_inf"
            )

        return value_decimal

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "number",
            "format": "decimal",
        }


def default_timezone() -> Any | None:
    return timezone.get_current_timezone() if settings.USE_TZ else None


class DateTimeField(Field):
    """
    Field that only accepts values that can be parsed into datetime
    """

    error_messages = {
        "wrong_format": (
            "Value %(value)s does not have the correct format,"
            " should be %(date_format)s"
        )
    }
    default_date_format = "%Y-%m-%dT%H:%M:%SZ"
    format = "date-time"

    def __init__(
        self,
        query_param_name: str,
        target_fields: str | tuple[str, ...] | list[str] | None = None,
        validators: list[Callable[[Any], None]] | None = None,
        description: str = "",
        example: str = "",
        date_format: str = "",
        make_aware: bool = True,
        connector: str = Q.AND,
    ) -> None:
        super().__init__(
            query_param_name,
            target_fields,
            validators,
            description,
            example,
            connector,
        )

        self.date_format = date_format or self.default_date_format
        self.make_aware = make_aware

    def validate(self, raw_value: Any) -> Any:
        try:
            dt = datetime.datetime.strptime(raw_value, self.date_format)
            if self.make_aware:
                _timezone = default_timezone()
                if _timezone and (dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None):
                    return timezone.make_aware(dt, _timezone)
            return dt
        except ValueError:
            raise ValidationError(
                self.error_messages["wrong_format"]
                % {"value": raw_value, "date_format": self.date_format},
                code="wrong_format",
            )

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "string",
            "format": self.format,
        }


class DateField(DateTimeField):
    """
    Field that only accepts values that can be parsed into date
    """

    default_date_format = "%Y-%m-%d"
    format = "date"

    def validate(self, raw_value: str) -> Any:
        try:
            return datetime.datetime.strptime(raw_value, self.date_format).date()
        except ValueError:
            raise ValidationError(
                self.error_messages["wrong_format"]
                % {"value": raw_value, "date_format": self.date_format},
                code="wrong_format",
            )


class ChoicesField(Field):
    """
    Field made to support multiple options.
    This can handle custom messages for the error raised
    """

    default_validate_message = _("Given value `{value}` is not a valid option")

    def __init__(
        self,
        query_param_name: str,
        target_fields: str | tuple[str, ...] | list[str] | None = None,
        validators: list[Callable[[Any], None]] | None = None,
        description: str = "",
        example: str = "",
        choices: (
            type[Choices] | list[tuple[str, Any]] | list[Any] | dict[str, Any] | None
        ) = None,
        validate_message: str = "",
        connector: str = Q.AND,
    ) -> None:
        super().__init__(
            query_param_name,
            target_fields,
            validators,
            description,
            example,
            connector,
        )

        if choices is None:
            raise TypeError("ChoicesField's choices requires to be set")

        if isinstance(choices, dict):
            self.choices = choices
        else:
            grouped_choices = to_choices_dict(choices)
            flatten_choices = flatten_choices_dict(grouped_choices)
            self.choices = self.choices_string_to_values = {
                str(key): value for key, value in flatten_choices.items()
            }

        self.validate_message = validate_message or self.default_validate_message

    def validate(self, raw_value: str) -> Any:
        try:
            return self.choices[raw_value]
        except KeyError:
            raise ValidationError(
                detail=self.validate_message.format(value=raw_value),
                code="not_in_choices",
            )

    def get_schema(self) -> dict[str, Any]:
        return {"type": "string", "enum": list(self.choices.keys())}


class BooleanField(ChoicesField):
    """
    Field that only accepts boolean related strings
    """

    TRUE_VALUES = ["true", "t", "1"]
    FALSE_VALUES = ["false", "f", "0"]
    default_validate_message = _("Given value `{value}` is not a valid boolean")

    def __init__(
        self,
        query_param_name: str,
        target_fields: str | tuple[str, ...] | list[str] | None = None,
        validators: list[Callable[[Any], None]] | None = None,
        description: str = "",
        example: str = "",
        invert: bool = False,
        validate_message: str = "",
        connector: str = Q.AND,
    ) -> None:
        choices = {}

        for key in self.TRUE_VALUES:
            choices[key] = True
        for key in self.FALSE_VALUES:
            choices[key] = False

        super().__init__(
            query_param_name,
            target_fields,
            validators,
            description,
            example,
            choices,
            validate_message,
            connector,
        )
        self.invert = invert

    def validate(self, raw_value: str) -> Any:
        return super().validate(raw_value.lower()) ^ self.invert


class ExistsField(Field):
    """
    Field that returns a set value if the field exists in the Query params.
    This Field doesn't care for the value given
    """

    def __init__(
        self,
        query_param_name: str,
        target_fields: str | list[str] | list[str] | None = None,
        validators: list[Callable[[Any], None]] | None = None,
        description: str = "",
        example: str = "",
        return_value: Any | None = None,
        connector: str = Q.AND,
    ) -> None:
        super().__init__(
            query_param_name,
            target_fields,
            validators,
            description,
            example,
            connector,
        )

        self.return_value = return_value

    def validate(self, raw_value: str) -> Any:
        return self.return_value


class ConcatField(Field):
    """
    Concatenate Fields and query from that result
    """

    def __init__(
        self,
        query_param_name: str,
        target_fields: list[Any] | Any,
        validators: list[Callable[[Any], None]] | None = None,
        lookup: str = "",
        target_field_name: str = "",
        output_field: DjangoField = DjangoCharField(),  # type: ignore
        description: str = "",
        example: str = "",
        connector: str = Q.AND,
    ) -> None:
        super().__init__(
            query_param_name,
            target_fields,
            validators,
            description,
            example,
            connector,
        )

        if not target_fields:
            raise ValueError("target_fields cannot be empty")

        self.lookup = lookup
        self.output_field = output_field

        if not target_field_name:
            self.target_field_name = "_{}".format(self.query_param_name)
        else:
            self.target_field_name = target_field_name

    def get_target_field(self) -> str:
        if self.lookup:
            return "{}__{}".format(self.target_field_name, self.lookup)
        return self.target_field_name

    def get_query(self, value: Any) -> Q:
        return Q(**{self.get_target_field(): value})

    def get_annotate(self) -> dict[str, Any]:
        concat = Concat(*self.target_fields, output_field=self.output_field)
        return {self.target_field_name: concat}


class RangeIntegerField(Range, IntegerField):
    pass


class RangeFloatField(Range, FloatField):
    pass


class RangeDecimalField(Range, DecimalField):
    pass


class RangeDateTimeField(Range, DateTimeField):
    pass


class RangeDateField(Range, DateField):
    pass


# === Just Keep... ===
class InIntegerField(ListField):
    def __init__(
        self,
        query_param_name: str,
        target_fields: str | tuple[str, ...] | list[str] | None = None,
        validators: list[Callable[[Any], None]] | None = None,
        description: str = "",
        example: str = "",
        connector: str = Q.AND,
    ) -> None:
        field = IntegerField(
            query_param_name,
            target_fields,
            validators,
            description,
            example,
            connector,
        )

        super().__init__(field)

        self.target_fields = [
            "{}__in".format(target_field) for target_field in self.target_fields
        ]


class InChoicesField(ListField):
    def __init__(
        self,
        query_param_name: str,
        choices: type[Choices] | list[tuple[str, Any]] | list[str] | dict[str, Any],
        target_fields: str | tuple[str, ...] | list[str] | None = None,
        validators: list[Callable[[Any], None]] | None = None,
        description: str = "",
        example: str = "",
        validate_message: str = "",
        connector: str = Q.AND,
    ) -> None:
        field = ChoicesField(
            query_param_name,
            target_fields,
            validators,
            description,
            example,
            choices,
            validate_message,
            connector,
        )

        super().__init__(field)

        self.target_fields = [
            "{}__in".format(target_field) for target_field in self.target_fields
        ]
