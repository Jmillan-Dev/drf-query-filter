from drf_query_filter.fields import (
    Field,
    ExistsField,
    FloatField,
    BooleanField,
    ChoicesField,
    DecimalField,
    IntegerField,
    ConcatField,
    DateTimeField,
    DateField,
    RangeFloatField,
    RangeIntegerField,
    RangeDecimalField,
    RangeDateTimeField,
    RangeDateField,
)


def test_generation_of_schema_list():
    fields = Field('z') | ((Field('a') | Field('b')) & (Field('c') |
                                                        Field('d')))
    fields &= Field('y')
    schema = fields.get_schema_operation_parameters()
    schema_target = [{
        'name': value,
        'required': False,
        'in': 'query',
        'description': '',
        'schema': {
            'type': 'string',
        },
        'example': '',
    } for value in ('z', 'a', 'b', 'c', 'd', 'y')]

    assert schema == schema_target, "Not equals!"


def test_all_fields_schema():
    field_classes = [
        Field,
        ExistsField,
        FloatField,
        BooleanField,
        ChoicesField,
        DecimalField,
        IntegerField,
        ConcatField,
        DateTimeField,
        DateField,
        RangeFloatField,
        RangeIntegerField,
        RangeDecimalField,
        RangeDateTimeField,
        RangeDateField,
    ]

    # try not to crash
    [y(str(x)).get_schema_operation_parameters() for x, y in enumerate(field_classes)]
