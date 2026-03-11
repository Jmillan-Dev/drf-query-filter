from drf_query_filter.fields import (  # ChoicesField,; ConcatField,; InChoicesField,
    BooleanField,
    DateField,
    DateTimeField,
    DecimalField,
    ExistsField,
    Field,
    FloatField,
    InIntegerField,
    IntegerField,
    RangeDateField,
    RangeDateTimeField,
    RangeDecimalField,
    RangeFloatField,
    RangeIntegerField,
    StringField,
)
from drf_query_filter.filters import QueryParamFilter


def test_generation_of_schema_list() -> None:
    fields = Field("z") | ((Field("a") | Field("b")) & (Field("c") | Field("d")))

    fields &= Field("y")
    result_schema = fields.get_schema_operation_parameters()

    expected_schema = [
        {
            "name": query_param,
            "required": False,
            "in": "query",
            "description": "",
            "schema": {
                "type": "string",
            },
            "example": "",
        }
        for query_param in ("z", "a", "b", "c", "d", "y")
    ]

    assert result_schema == expected_schema, "Not equals!"


def test_all_fields_schema() -> None:
    field_classes = [
        StringField,
        ExistsField,
        FloatField,
        BooleanField,
        # ChoicesField,
        DecimalField,
        IntegerField,
        # ConcatField,
        DateTimeField,
        DateField,
        RangeFloatField,
        RangeIntegerField,
        RangeDecimalField,
        RangeDateTimeField,
        RangeDateField,
        InIntegerField,
        # InChoicesField,
    ]

    # TODO Fix this implementation
    # try not to crash
    [y(str(x)).get_schema_operation_parameters() for x, y in enumerate(field_classes)]


def test_empty_filter() -> None:
    class View:
        pass

    q = QueryParamFilter()
    q.get_schema_operation_parameters(View())
