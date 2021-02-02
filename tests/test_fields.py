from datetime import datetime
from decimal import Decimal

from django.core.validators import (
    EmailValidator,
    URLValidator,
    MaxValueValidator,
    MinValueValidator,
)
from django.db.models import Q
from django.test import TestCase, override_settings
from django.utils import timezone

from drf_query_filter.fields import (
    Empty,
    Field,
    ExistsField,
    FloatField,
    BooleanField,
    ChoicesField,
    DecimalField,
    IntegerField,
    ConcatField,
    DateTimeField,
    RangeFloatField,
    RangeIntegerField,
    RangeDecimalField,
    RangeDateTimeField,
    default_timezone,
)


class FieldTests(TestCase):
    
    def test_target_field(self):
        """
        Testing the creation of the target fields
        """
        self.assertEqual(Field('field', 'target_field').target_fields, ['target_field'])
        self.assertEqual(Field('field').target_fields, ['field'])
        self.assertEqual(Field('field', ['one', 'two']).target_fields, ['one', 'two'])
        self.assertEqual(Field('field', ('target_field',)).target_fields, ('target_field',))
    
    def test_call(self):
        """
        Testing the __call__ method
        """
        field = Field('field')
        self.assertTrue(field({'field': 'value'}))
        self.assertEqual(field._raw_value, 'value')
        self.assertFalse(field({}))
        self.assertTrue(isinstance(field._raw_value, Empty))
        self.assertFalse(field({'other_field': 'value'}))
        self.assertTrue(isinstance(field._raw_value, Empty))
    
    def test_validators(self):
        """ Testing to see if Django validators are working with the fields """
        field = Field('field', validators=[EmailValidator()])
        field({'field': 'test@email.gg'})
        self.assertTrue(field.is_valid())
        field({'field': 'not_an_email'})
        self.assertFalse(field.is_valid())
        self.assertEqual(field._errors[0].code, 'invalid', field._errors)
        
        field = Field('field', validators=[URLValidator(code='awful')])
        field({'field': 'https://127.0.0.1:8000/'})
        self.assertTrue(field.is_valid())
        field({'field': 'not_an_url'})
        self.assertFalse(field.is_valid())
        self.assertEqual(field._errors[0].code, 'awful', field._errors)
    
    def test_get_query(self):
        """ Test the generation of queries """
        field = Field('field', 'target_field')
        field({'field': 'value'})
        field.is_valid()
        self.assertEqual(str(field.get_query()), str(Q(target_field='value')))
        field = Field('field', ['target_one', 'target_two'])
        field({'field': 'value'})
        field.is_valid()
        self.assertEqual(str(field.get_query()), str(Q(target_one='value') & Q(target_two='value')))
        field = Field('field')
        field({'field': 'value'})
        field.is_valid()
        self.assertEqual(str(field.get_query()), str(Q(field='value')))


class ExistsFieldTests(TestCase):
    
    def test_get_value_query(self):
        field = ExistsField('field', return_value='My_custom_value')
        self.assertTrue(field({'field': None}))
        self.assertTrue(field.is_valid())
        self.assertEqual(field.value, None)
        self.assertEqual(field.get_value_query(), 'My_custom_value')
        self.assertEqual(str(field.get_query()), str(Q(field='My_custom_value')))


class NumericFieldsTests(TestCase):
    
    def test_integer_validate(self):
        field = IntegerField('field')
        field({'field': '0123'})
        self.assertTrue(field.is_valid(), field._errors)
        self.assertEqual(field.value, 123)
        field({'field': '10.69'})
        self.assertFalse(field.is_valid())
        self.assertEqual(field._errors[0].code, 'invalid')
        field({'field': 'not_a_number'})
        self.assertFalse(field.is_valid())
        self.assertEqual(field._errors[0].code, 'invalid')
    
    def test_float_validate(self):
        field = FloatField('field')
        field({'field': '0123'})
        self.assertTrue(field.is_valid(), field._errors)
        self.assertEqual(field.value, 123)
        field({'field': '10.69'})
        self.assertTrue(field.is_valid(), field._errors)
        self.assertEqual(field.value, float('10.69'))
        field({'field': 'not_a_number'})
        self.assertFalse(field.is_valid())
        self.assertEqual(field._errors[0].code, 'invalid')
    
    def test_decimal_validate(self):
        field = DecimalField('field')
        field({'field': '0123'})
        self.assertTrue(field.is_valid())
        self.assertEqual(field.value, Decimal('0123'))
        field({'field': '10.69'})
        self.assertTrue(field.is_valid(), field._errors)
        self.assertEqual(field.value, Decimal('10.69'))
        field({'field': 'not_a_number'})
        self.assertFalse(field.is_valid())
        self.assertEqual(field._errors[0].code, 'invalid')
    
    def test_validators(self):
        """ Using numeric validators of Django """
        for field_class in [IntegerField, FloatField, DecimalField]:
            field = field_class('field', validators=[MinValueValidator(3), MaxValueValidator(10)])
            field({'field': '10'})
            self.assertTrue(field.is_valid(), field._errors)
            field({'field': '0'})
            self.assertFalse(field.is_valid())
            self.assertEqual(field._errors[0].code, 'min_value')
            field({'field': '100'})
            self.assertFalse(field.is_valid())
            self.assertEqual(field._errors[0].code, 'max_value')


class BooleanFieldTests(TestCase):
    
    def test_validate(self):
        field = BooleanField('field')
        for value in ['true', 'false', 'FaLsE', '0', '1']:
            field({'field': value})
            self.assertTrue(field.is_valid(), value)
        for value in ['verdadero', 'falso', '____', '']:
            field({'field': value})
            self.assertFalse(field.is_valid(), value)
    
    def test_value(self):
        field = BooleanField('field')
        field({'field': 'True'})
        field.is_valid()
        self.assertTrue(field.value)
        field({'field': 'False'})
        field.is_valid()
        self.assertFalse(field.value)


class ChoicesFieldTests(TestCase):
    
    def test_validate(self):
        field = ChoicesField('field', choices=['green', 'red', 'yellow'])
        for value in ['Green', 'rEd', 'YELLOW', 'yellow']:
            field({'field': value})
            self.assertTrue(field.is_valid())
        for value in ['greenly', '']:
            field({'field': value})
            self.assertFalse(field.is_valid())
            self.assertEqual(field._errors[0].code, 'not_in_choices')
        field = ChoicesField('field', choices=['car', 'Plane', 'BOAT'], case_sensitive=True)
        for value in ['Car', 'plane', 'bOAT']:
            field({'field': value})
            self.assertFalse(field.is_valid())
            self.assertEqual(field._errors[0].code, 'not_in_choices')


class CombinedFieldTests(TestCase):
    
    def test_annotate(self):
        # we cannot really compare the Concat values so we just compare the result field name generated
        field = ConcatField('field', ['field_one', 'field_two'])
        self.assertTrue('field_one_field_two', field.get_annotate())
        field = ConcatField('field', ['field_one__element', 'field__other'])
        self.assertTrue('field_one_element_field_other', field.get_annotate())
        field = ConcatField('field', ['field_one', 'field_two'], target_field_name='field_annotate')
        self.assertIn('field_annotate', field.get_annotate())
    
    def test_get_query(self):
        field = ConcatField('field', ['field_one', 'field_two'])
        field({'field': 'value'})
        field.is_valid()
        self.assertEqual(str(field.get_query()), str(Q(field_one_field_two='value')))
        field = ConcatField('field', ['field_one', 'field_two'], lookup='icontains')
        field({'field': 'value'})
        field.is_valid()
        self.assertEqual(str(field.get_query()), str(Q(field_one_field_two__icontains='value')))


class DateTimeFieldTests(TestCase):
    
    def test_validate(self):
        field = DateTimeField('field')
        field({'field': '2020-12-31'})
        self.assertTrue(field.is_valid(), field._errors)
        self.assertEqual(field.value, datetime(year=2020, month=12, day=31))
        field({'field': '2020-30-12'})
        self.assertFalse(field.is_valid())
        self.assertEqual(field._errors[0].code, 'wrong_format', field._errors)
        field({'field': '31-12-2020'})
        self.assertFalse(field.is_valid())
        self.assertEqual(field._errors[0].code, 'wrong_format', field._errors)
        
    @override_settings(USE_TZ=True)
    def test_validate_forcing_timezone(self):
        field = DateTimeField('field')
        field({'field': '2020-1-1'})
        self.assertTrue(field.is_valid(), field._errors)
        self.assertNotEqual(field.value, datetime(year=2020, month=1, day=1))
        self.assertEqual(field.value, timezone.make_aware(datetime(year=2020, month=1, day=1), default_timezone()))


class TestingRangeMixin(TestCase):
    
    def validate(self, field_class, values, is_true=True):
        field = field_class('field')
        field({'field': values})
        if is_true:
            self.assertTrue(field.is_valid(), field._errors)
    
    def test_validate(self):
        field_classes = [RangeIntegerField, RangeFloatField, RangeDecimalField]
        for field_class in field_classes:
            field = field_class('field')
            field({'field': '1,10'})
            self.assertTrue(field.is_valid(), field._errors)
            field({'field': ',10'})
            self.assertTrue(field.is_valid(), field._errors)
            field({'field': '1,'})
            self.assertTrue(field.is_valid(), field._errors)
            
        field = RangeDateTimeField('field')
        field({'field': '2020-1-1,2020-12-31'})
        self.assertTrue(field.is_valid(), field._errors)
        field({'field': ',2020-12-31'})
        self.assertTrue(field.is_valid(), field._errors)
        field({'field': '2020-1-1,'})
        self.assertTrue(field.is_valid(), field._errors)

    def get_validate_query(self, field_class, value_a, value_b):
        field = field_class('field', equal=False)
        field({'field': '%s,%s' % (value_a, value_b)})
        self.assertTrue(field.is_valid(), field._errors)
        self.assertEqual(str(field.get_query()),
                         str(Q(**{'field__gt': value_a, 'field__lt': value_b})))
        field = field_class('field', equal=True)
        field({'field': '%s,%s' % (value_a, value_b)})
        self.assertTrue(field.is_valid(), field._errors)
        self.assertEqual(str(field.get_query()),
                         str(Q(**{'field__gte': value_a, 'field__lte': value_b})))

    def test_get_query(self):
        self.get_validate_query(RangeIntegerField, 1, 10)
        self.get_validate_query(RangeFloatField, 1.0, 10.0)
        self.get_validate_query(RangeDecimalField, Decimal(1), Decimal(10))
