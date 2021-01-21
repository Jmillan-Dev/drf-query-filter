import datetime
import re
from typing import List, Callable, Union, Tuple, Dict, Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import CharField
from django.db.models.functions import Concat
from django.db.models.query_utils import Q
from rest_framework.exceptions import ValidationError
from rest_framework.fields import get_error_detail

import mixins
from utils import QueryType


class Field:
    def __init__(self,
                 field_name: str,
                 target_fields: Union[str, List, Tuple],
                 required: bool = False,
                 validators: List[Callable] = None,
                 union_type: QueryType = QueryType.AND):
        """
        Base field
        :param field_name: The name in the query params of the url
        :param target_fields: The target fields in the queryset, This can be a str alone or multiple of them
        :param required: If this is a required field for the queryset
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
        self.required: bool = required  # this creates some validation if the value is not found but it is required
        
        self._value: Any = None  # value got from the query param request
        self.value: Any = None  # transformed value
        self.no_value: bool = True  # Flag to check if this
        self.errors: List = []  # the list of errors we got
    
    def __call__(self, query_data: Dict) -> None:
        """
        Try to find the value from the given field, if it doesn't find it it sets the flag no_value as True
        :param query_data:
        :return:
        """
        
        if self.field_name in query_data:
            self._value = query_data[self.field_name]
            self.no_value = False
        else:
            self._value = None
            self.no_value = True
    
    def validate(self, value: Any) -> None:
        """
        Function for custom validations, if there is any error it should throw an ValidationError Exception.
        This can also manipulate the value if required.
        """
        return value
    
    def run_validators(self, value: Any) -> None:
        """ This uses the validation style like in the fields of rest_framework """
        if self.validators:
            for validator in self.validators:
                # run all the validations and gather all the errors if there are any
                try:
                    validator(value)
                except ValidationError as exc:
                    self.errors.extend(exc.detail)
                except DjangoValidationError as exc:
                    self.errors.extend(get_error_detail(exc))
    
    def is_valid(self) -> bool:
        self.errors = []  # Clean all the previous errors
        
        if self.no_value and self.required:
            self.errors.extend(ValidationError('This field is required', 'required').detail)
        elif not self.no_value:
            try:
                self.value = self.validate(self._value)
            except ValidationError as exc:
                self.errors.extend(exc.detail)
            except DjangoValidationError as exc:
                self.errors.extend(get_error_detail(exc))
            else:
                self.run_validators(self.value)
        
        return len(self.errors) == 0
    
    def get_value_query(self) -> Any:
        """ This should be overwritten if the desire data needs to be manipulated for the query """
        return self.value
    
    def get_query(self) -> Q:
        query = Q()
        if not self.no_value:
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


class NumberField(Field):
    """
    Field that only accepts numbers as values
    """
    
    def validate(self, value):
        """ by default this will try to get the data to be a number always """
        try:
            return float(value)
        except ValueError:
            raise ValidationError('Value `%s` is not a valid number' % value, code='wrong_type')


class RangeNumberField(mixins.Range,
                       NumberField):
    """
    Accepts two values of numbers in the string and check them with greater than or lesser than in the query
    """


class DateField(Field):
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
                                  (value, self.date_format))


class RangeDateField(mixins.Range,
                     DateField):
    """
    Accepts two values of dates in the string and check them with greater than or lesser than in the query
    """
    pass


class OptionsField(Field):
    """
    Field made to support multiple options.
    this can handle case sensitive and custom messages for the error thrown
    """
    
    default_values = []
    default_case_sensitive = False
    default_validate_message = 'Value `%s` is not a valid option, Options are: %s'
    
    def __init__(self, *args,
                 valid_values: List[str] = None,
                 case_sensitive: bool = None,
                 validate_message: str = "",
                 **kwargs):
        self.values = valid_values or self.default_values
        self.case_sensitive = case_sensitive or self.default_case_sensitive
        self.validate_message = validate_message or self.default_validate_message
        super().__init__(*args, **kwargs)
    
    def validate(self, value):
        valid_values = self.values
        if not self.case_sensitive:
            value = value.lower()
            valid_values = [valid_value.lower() for valid_value in valid_values]
        
        if value not in valid_values:
            raise ValidationError(detail=self.validate_message % (value, self.values),
                                  code='not_in_options')
        return valid_values


class BooleanField(OptionsField):
    """
    Field that only accepts boolean related strings
    Field that only accepts some valid values in the data of query params
    this values are boolean related
    """
    
    def __init__(self, *args, **kwargs):
        # ignore the kwargs of valid_values
        kwargs['valid_values'] = ['true', 'false', '1', '0']
        kwargs['validate_message'] = 'Value `%s` is not a valid boolean. Options are: %s'
        kwargs['case_sensitive'] = False
        super().__init__(*args, **kwargs)


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
        self.suffix = kwargs.pop('suffix', '')
        self.target_field_name = kwargs.pop('target_field_name', '')
        super().__init__(*args, **kwargs)
        if not self.target_field_name:
            self.target_field_name = re.sub(r'__+', '_', re.sub(self.invalid_characters, '_',
                                                                '_'.join([str(value) for value in self.target_fields])))
    
    def get_suffix(self):
        return '__%s' % self.suffix if self.suffix else ''
    
    def get_query(self):
        query = Q()
        if not self.no_value:
            query &= Q(**{'%s%s' % (self.target_field_name, self.get_suffix()): self.get_value_query()})
        return query
    
    def get_annotate(self):
        # concat values here
        concat = Concat(*self.target_fields, output_field=CharField())
        return {self.target_field_name: concat}
