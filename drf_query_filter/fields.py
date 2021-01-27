import datetime
import re
import decimal
from typing import List, Callable, Union, Tuple, Dict, Any, Optional

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models.fields import CharField as DjangoCharField
from django.db.models.functions import Concat
from django.db.models.query_utils import Q
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError
from rest_framework.fields import get_error_detail

from drf_query_filter import mixins
from drf_query_filter.utils import QueryType


class Empty:
    """ Dummy class just to represent a True None value """
    pass


class Field:
    def __init__(self,
                 field_name: str,
                 target_fields: Optional[Union[str, List, Tuple]] = None,
                 validators: List[Callable] = None,
                 union_type: QueryType = QueryType.AND):
        """
        Base field
        :param field_name: The name in the query params of the url
        :param target_fields: The target fields in the queryset, This can be a str alone or multiple of them
        :param validators: A list of class validators to call in the validation process
        :param union_type: Type of union in the target fields
        """
        self.field_name: str = field_name
        assert self.field_name, '%s.field_name cannot be empty.' % self.__class__.__name__
        
        self.target_fields = target_fields or self.field_name
        
        assert isinstance(self.target_fields, str) or \
               isinstance(self.target_fields, list) or \
               isinstance(self.target_fields, tuple), (
            'given target_fields is a `%s`, it should be a str or a list/tuple.' % type(self.target_fields)
        )
        
        if isinstance(self.target_fields, str):
            self.target_fields = [self.target_fields]
        
        self.validators: List[Callable] = validators
        self.query_type: QueryType = union_type
        
        self._raw_value: Any = Empty()  # value got from the query param request
        self._value: Any = self._raw_value  # transformed value
        self.no_value: bool = True  # Flag to check if this
        self.errors: List = []  # the list of errors we got
    
    def __call__(self, query_data: Dict) -> bool:
        """
        Try to find the value from the given field, if it doesn't find it it sets the flag no_value as True
        """
        
        if self.field_name in query_data:
            self._raw_value = query_data[self.field_name]
            return True
        else:
            self._raw_value = Empty()
            return False
    
    def validate(self, value: Any) -> None:
        """
        Function for custom validations, if there is any error it should throw a ValidationError Exception.
        This can also manipulate the value if required.
        """
        return value
    
    def run_validators(self, value: Any) -> None:
        """ This uses the validation style like in the fields of rest_framework """
        if self.validators:
            for validator in self.validators:
                # run all the validators and gather all the errors thrown by them
                try:
                    validator(value)
                except ValidationError as exc:
                    self.errors.extend(exc.detail)
                except DjangoValidationError as exc:
                    self.errors.extend(get_error_detail(exc))
    
    def is_valid(self) -> bool:
        self.errors = []  # Clean all the previous errors
        
        assert not isinstance(self._raw_value, Empty),\
            'you cannot call is_valid without giving a value first'
        
        try:
            self._value = self.validate(self._raw_value)
        except ValidationError as exc:
            self.errors.extend(exc.detail)
        except DjangoValidationError as exc:
            self.errors.extend(get_error_detail(exc))
        else:
            self.run_validators(self._value)
        
        return len(self.errors) == 0
    
    @property
    def value(self) -> Any:
        assert not isinstance(self._value, Empty), 'you must call is_valid first'
        return self._value
    
    def get_value_query(self) -> Any:
        """ This should be overwritten if the desire data needs to be manipulated for the query """
        return self.value
    
    def get_query(self) -> Q:
        query = Q()
        value = self.get_value_query()
        for field in self.target_fields:
            if self.query_type == QueryType.AND:
                query &= Q(**{field: value})
            elif self.query_type == QueryType.OR:
                query |= Q(**{field: value})
        
        return query
    
    def get_annotate(self) -> Dict:
        """ This should be overwritten if the field requires to annotate custom fields in the query """
        return {}


class IntegerField(Field):
    """
    Field that only accepts integers as values
    """
    error_messages = {
        'invalid': _('“%(value)s” value must be an integer.'),
    }
    
    def validate(self, value):
        try:
            return int(value)
        except (TypeError, ValueError):
            raise ValidationError(self.error_messages['invalid'] % {'value': value}, code='invalid')


class RangeIntegerField(mixins.Range,
                        IntegerField):
    """
    Accepts two integer values in the string and generate a query with greater than or lesser than in the target fields.
    """
    pass


class FloatField(Field):
    """
    Field that only accepts floats values
    """
    error_messages = {
        'invalid': _('“%(value)s” value must be a float.'),
    }
    
    def validate(self, value):
        """ Try to parse the value into a float """
        try:
            return float(value)
        except (TypeError, ValueError):
            raise ValidationError(self.error_messages['invalid'] % {'value': value}, code='invalid')


class RangeFloatField(mixins.Range,
                      FloatField):
    """
    Accepts two float values in the string and generate a query with greater than or lesser than in the target fields.
    """
    pass


# TODO is still missing some validation unique to the Decimal type
class DecimalField(Field):
    """
    Field that only accepts Decimal values
    """
    error_messages = {
        'invalid': _('“%(value)s” value must be a double.'),
    }
    
    def validate(self, value):
        try:
            return decimal.Decimal(value)
        except (decimal.InvalidOperation, TypeError, ValueError):
            raise ValidationError(self.error_messages['invalid'] % {'value': value}, code='invalid')


class RangeDecimalField(mixins.Range,
                        DecimalField):
    """
    Accepts two Decimal values in the string and generate a query with greater than or lesser than in the target fields.
    """
    pass


class DateTimeField(Field):
    """
    Field that only accepts values that can be parsed into date time
    """
    default_date_format = '%Y-%m-%d'
    
    def __init__(self, *args, date_format: str = None, **kwargs):
        self.date_format = date_format or self.default_date_format
        super().__init__(*args, **kwargs)
    
    def validate(self, value):
        try:
            return datetime.datetime.strptime(value, self.date_format)
        except ValueError:
            raise ValidationError('Value %s does not have the correct format, should be %s' %
                                  (value, self.date_format), code='wrong_format')


class RangeDateTimeField(mixins.Range,
                         DateTimeField):
    """
    Accepts two dates values in the string and generate a query with greater than or lesser than in the target fields.
    """
    pass


class ChoicesField(Field):
    """
    Field made to support multiple options.
    this can handle case sensitive and custom messages for the error thrown
    """
    
    default_values = []
    default_case_sensitive = False
    default_validate_message = 'Value `%s` is not a valid option, Options are: %s'
    
    def __init__(self, *args,
                 choices: List[str] = None,
                 case_sensitive: bool = None,
                 validate_message: str = "",
                 **kwargs):
        self.choices = choices or self.default_values
        self.case_sensitive = case_sensitive or self.default_case_sensitive
        self.validate_message = validate_message or self.default_validate_message
        super().__init__(*args, **kwargs)
    
    def validate(self, value):
        clean_choices = self.choices
        # If case sensitive is on lower the values in the incoming value
        # and make sure that choices are also clean
        if not self.case_sensitive:
            value = value.lower()
            clean_choices = [valid_value.lower() for valid_value in clean_choices]
        
        if value not in clean_choices:
            raise ValidationError(detail=self.validate_message % (value, self.choices),
                                  code='not_in_choices')
        return value


class BooleanField(ChoicesField):
    """
    Field that only accepts boolean related strings
    Field that only accepts some valid values in the data of query params
    this values are boolean related
    """
    
    def __init__(self, *args, **kwargs):
        # ignore the kwargs of choices
        kwargs['choices'] = ['true', 'false', '1', '0']
        kwargs['validate_message'] = 'Value `%s` is not a valid boolean. Options are: %s'
        kwargs['case_sensitive'] = False
        super().__init__(*args, **kwargs)
    
    def validate(self, value):
        value = super().validate(value)
        return value in ['true', '1']


class ExistsField(Field):
    """
    Field that returns a set value if the field exists in the Query params
    """
    
    def __init__(self, *args, return_value=None, **kwargs):
        self.return_value = return_value
        super().__init__(*args, **kwargs)
    
    def get_value_query(self):
        return self.return_value


class CombinedField(Field):
    """
    Combine Fields and query from that result
    """
    invalid_characters = r'[\( \)\\/]'
    
    def __init__(self, *args, **kwargs):
        self.suffix = kwargs.pop('lookup', '')
        self.target_field_name = kwargs.pop('target_field_name', '')
        self.output_field = kwargs.pop('output_field', DjangoCharField())
        super().__init__(*args, **kwargs)
        if not self.target_field_name:
            self.target_field_name = re.sub(r'__+', '_', re.sub(self.invalid_characters, '_',
                                                                '_'.join([str(value) for value in self.target_fields])))
    
    def get_suffix(self):
        return '__%s' % self.suffix if self.suffix else ''
    
    def get_query(self):
        query = Q(**{'%s%s' % (self.target_field_name, self.get_suffix()): self.get_value_query()})
        return query
    
    def get_annotate(self):
        # concat values here
        concat = Concat(*self.target_fields, output_field=self.output_field)
        return {self.target_field_name: concat}
