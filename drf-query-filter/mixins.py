from django.db.models import Q
from rest_framework.exceptions import ValidationError

from utils import QueryType


class Range:
    default_list_separator = ','
    
    def __init__(self, *args,
                 list_separator: str = None,
                 than_equal: bool = False,
                 allow_empty: bool = True,
                 **kwargs):
        self.list_separator = list_separator or self.default_list_separator
        self.equal = than_equal
        self.allow_empty = allow_empty
        self.target_fields = None
        super().__init__(*args, **kwargs)
    
    def get_target_fields(self):
        if self.equal:
            return [('%s__gte' % target_field, '%s__lte' % target_field) for target_field in self.target_fields]
        else:
            return [('%s__gt' % target_field, '%s__lt' % target_field) for target_field in self.target_fields]
    
    def validate(self, value):
        """ we need to divide the value into two values """
        value = value.split(self.list_separator)

        # check length
        if len(value) < 2:
            raise ValidationError('Not enough values, was only given `%s`, it needs at least 2' % len(value),
                                  code='not_enough_values')
        
        # check if the values are numbers
        for v in value:
            if self.allow_empty and len(v) == 0:  # I don't like this... but I'm tired to think in a better solution.
                pass
            else:
                super().validate(v)
        return value
    
    def get_query(self):
        query = Q()
        if not self.no_value:
            values = self.value
            for target_field_gt, target_field_lt in self.get_target_fields():
                query_dict = {}
                if values[0]:
                    query_dict[target_field_gt] = values[0]
                if values[1]:
                    query_dict[target_field_lt] = values[1]
                if self.query_type == QueryType.AND:
                    query &= Q(**query_dict)
                elif self.query_type == QueryType.OR:
                    query |= Q(**query_dict)
        return query


