from drf_query_filter.fields import (
    Field,
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
        }
    } for value in ('z', 'a', 'b', 'c', 'd', 'y')]

    assert schema == schema_target, "Not equals!"


