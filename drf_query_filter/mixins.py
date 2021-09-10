from django.db.models import Q
from rest_framework.exceptions import ValidationError
from rest_framework.compat import coreschema

from drf_query_filter.utils import ConnectorType


class Range:
    default_list_separator = ','

    def __init__(self, *args,
                 list_separator: str = None,
                 equal: bool = False,
                 allow_empty: bool = True,
                 **kwargs):
        self.list_separator = list_separator or self.default_list_separator
        self.equal = equal
        self.allow_empty = allow_empty
        self.target_fields = None
        super().__init__(*args, **kwargs)

    def get_target_fields(self):
        if self.equal:
            return [('%s__gte' % target_field, '%s__lte' % target_field) for target_field
                    in self.target_fields]
        else:
            return [('%s__gt' % target_field, '%s__lt' % target_field) for target_field
                    in self.target_fields]

    def validate(self, value):
        """ we need to divide the value into two values """
        value = value.split(self.list_separator)

        # check length
        if len(value) < 2:
            raise ValidationError(
                'Not enough values, was only given `%s`, it needs at least 2' % len(value),
                code='not_enough_values')

        new_values = []
        for v in value:
            if self.allow_empty and len(v) == 0:
                new_values.append(None)  # ignore the value but push a null value
            else:
                new_values.append(super().validate(v))
        return new_values

    def get_query(self):
        query = Q(_connector=self.connector)
        for target_field_gt, target_field_lt in self.get_target_fields():
            query_dict = {}
            if self.value[0]:
                query_dict[target_field_gt] = self.value[0]
            if self.value[1]:
                query_dict[target_field_lt] = self.value[1]

            if self.connector == ConnectorType.AND:
                query &= Q(**query_dict)
            elif self.connector == ConnectorType.OR:
                query |= Q(**query_dict)
        return query

    def get_description(self):
        """ We update the original description by adding a format into it... since the
        swagger specification does not support our interesting and complicated way to
        pass a range values"""
        original_type = super().get_schema()
        if 'format' in original_type:
            schema_type = '%s:%s' % (
                original_type.get('type', ''),
                original_type['format']
            )
        else:
            schema_type = original_type.get('type', '')
        return '%s\n Format: %s' % (
            super().get_description(),
            schema_type,
        )

    def get_coreschema_field(self):
        return coreschema.String(
            format=r'(\w*),(\w*)'
        )

    def get_schema(self):
        return {
            'type': 'string',
            'format': r'(\w*),(\w*)',
        }
