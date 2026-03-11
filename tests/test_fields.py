import datetime
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo


from django.core.validators import (
    EmailValidator,
    MaxValueValidator,
    MinValueValidator,
    URLValidator,
)
from django.db.models import (
    IntegerChoices,
    Q,
)
from django.test import (
    TestCase,
    override_settings,
)
from django.utils import timezone


from drf_query_filter.fields import (
    BooleanField,
    ChoicesField,
    ConcatField,
    DateField,
    DateTimeField,
    DecimalField,
    ExistsField,
    Field,
    FloatField,
    InChoicesField,
    InIntegerField,
    IntegerField,
    RangeDateField,
    RangeDecimalField,
    RangeFloatField,
    RangeIntegerField,
    StringField,
    default_timezone,
)
from drf_query_filter.mixins import Range


class StringFieldTests(TestCase):
    def test_target_field(self) -> None:
        """
        Testing the creation of the target fields
        """
        self.assertEqual(
            StringField("field", "target_field").target_fields, ["target_field"]
        )
        self.assertEqual(StringField("field").target_fields, ["field"])
        self.assertEqual(
            StringField("field", ["one", "two"]).target_fields, ["one", "two"]
        )
        self.assertEqual(
            StringField("field", ("target_field",)).target_fields,
            ("target_field",),
        )

    def test_validators(self) -> None:
        """Testing to see if Django validators are working with the fields"""
        field = StringField("email", validators=[EmailValidator()])
        _, _, errors = field.get_filter({"email": "test@email.gg"})
        self.assertFalse(errors, errors)
        _, _, errors = field.get_filter({"email": "not an email"})
        self.assertTrue(errors, "Expected errors")
        self.assertEqual(errors["email"][0].code, "invalid", errors)

        field = StringField("url", validators=[URLValidator(code="awful")])
        _, _, errors = field.get_filter({"url": "https://127.0.0.1:8000/"})
        self.assertEqual(len(errors), 0)
        _, _, errors = field.get_filter({"url": "not_an_url"})
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors["url"][0].code, "awful", errors)

    def test_get_query(self) -> None:
        """Test the generation of queries"""
        field = StringField("field", "target_field")
        query = field.get_query("value")
        self.assertEqual(str(query), str(Q(target_field="value")))

        field = StringField("field", ["target_one", "target_two"])
        query = field.get_query("value")
        self.assertEqual(
            str(query),
            str(Q(target_one="value") & Q(target_two="value")),
        )

        field = StringField("field")
        query = field.get_query("value")
        self.assertEqual(str(query), str(Q(field="value")))


class ExistsFieldTests(TestCase):
    def test_get_value_query(self) -> None:
        field = ExistsField("field", return_value="My_custom_value")

        query, annotate, errors = field.get_filter({"field": ""})
        self.assertEqual(len(errors), 0)
        self.assertEqual(str(query), str(Q(field="My_custom_value")))


class NumericFieldsTests(TestCase):
    def test_integer_validate(self) -> None:
        field = IntegerField("field")

        errors, value = field.perform_validation("0123")
        self.assertEqual(len(errors), 0, errors)
        self.assertEqual(value, 123)

        errors, value = field.perform_validation("10.99")
        self.assertNotEqual(len(errors), 0, "Expected errors")
        self.assertEqual(errors[0].code, "invalid")

        errors, value = field.perform_validation("not a number")
        self.assertNotEqual(len(errors), 0, "Expected errors")
        self.assertEqual(errors[0].code, "invalid")

    def test_float_validate(self) -> None:
        field = FloatField("field")

        errors, value = field.perform_validation("0123")
        self.assertEqual(len(errors), 0, errors)
        self.assertEqual(value, 123)

        errors, value = field.perform_validation("10.99")
        self.assertEqual(len(errors), 0, errors)
        self.assertEqual(value, float("10.99"))

        errors, value = field.perform_validation("not_a_number")
        self.assertNotEqual(len(errors), 0, "Expected errors")
        self.assertEqual(errors[0].code, "invalid")

    def test_decimal_validate(self) -> None:
        field = DecimalField("field")

        errors, value = field.perform_validation("0123")
        self.assertEqual(len(errors), 0, errors)
        self.assertEqual(value, Decimal("0123"))

        errors, value = field.perform_validation("10.99")
        self.assertEqual(len(errors), 0, errors)
        self.assertEqual(value, Decimal("10.99"))

        errors, value = field.perform_validation("not_a_number")
        self.assertNotEqual(len(errors), 0, "Expected errors")
        self.assertEqual(errors[0].code, "invalid")

        errors, value = field.perform_validation("inf")
        self.assertNotEqual(len(errors), 0, "Expected errors")
        self.assertEqual(errors[0].code, "is_inf")

        errors, value = field.perform_validation("Nan")
        self.assertNotEqual(len(errors), 0, "Expected errors")
        self.assertEqual(errors[0].code, "is_nan")

    def test_validators(self) -> None:
        """Using numeric validators of Django"""
        for field_class in [IntegerField, FloatField, DecimalField]:
            field = field_class(
                "field",
                validators=[MinValueValidator(3), MaxValueValidator(10)],
            )
            errors, _ = field.perform_validation("10")
            self.assertEqual(len(errors), 0, errors)
            errors, _ = field.perform_validation("0")
            self.assertNotEqual(len(errors), 0, "Expected errors")
            self.assertEqual(errors[0].code, "min_value")
            errors, _ = field.perform_validation("100")
            self.assertNotEqual(len(errors), 0, "Expected errors")
            self.assertEqual(errors[0].code, "max_value")


class ChoicesFieldTests(TestCase):
    def test_validate(self) -> None:
        field = ChoicesField("field", choices=["green", "red", "yellow"])

        for value in ["green", "red", "yellow"]:
            errors, _ = field.perform_validation(value)
            self.assertEqual(len(errors), 0, errors)

        for value in ["greenly", ""]:
            errors, _ = field.perform_validation(value)
            self.assertNotEqual(len(errors), 0, "Expected errors")
            self.assertEqual(errors[0].code, "not_in_choices")

        field = ChoicesField("field", choices=["car", "Plane", "BOAT"])
        for value in ["Car", "plane", "bOAT"]:
            errors, _ = field.perform_validation(value)
            self.assertNotEqual(len(errors), 0, "Expected errors")
            self.assertEqual(errors[0].code, "not_in_choices", errors)

    def test_with_django_choices_class(self) -> None:
        class TestChoices(IntegerChoices):
            ONE = 1
            TWO = (2, "dos")

        field = ChoicesField("field", choices=TestChoices)

        for value in ["1", "2"]:
            errors, _ = field.perform_validation(value)
            self.assertEqual(len(errors), 0, errors)

        for value in ["ONE", "3"]:
            errors, _ = field.perform_validation(value)
            self.assertNotEqual(len(errors), 0, "Expected errors")
            self.assertEqual(errors[0].code, "not_in_choices", errors)


class BooleanFieldTests(TestCase):
    def test_validate(self) -> None:
        field = BooleanField("field")

        for value in ["true", "false", "0", "1", "True", "False"]:
            errors, _ = field.perform_validation(value)
            self.assertEqual(len(errors), 0, errors)
        for value in ["verdadero", "falso", "____", ""]:
            errors, _ = field.perform_validation(value)
            self.assertNotEqual(len(errors), 0, "Expected errors")
            self.assertEqual(errors[0].code, "not_in_choices", errors)

    def test_invert(self) -> None:
        field = BooleanField("field", invert=True)

        errors, value = field.perform_validation("true")
        self.assertEqual(len(errors), 0, errors)
        self.assertFalse(value)

        errors, value = field.perform_validation("false")
        self.assertEqual(len(errors), 0, errors)
        self.assertTrue(value)


class ConcatFieldTests(TestCase):
    def test_annotate(self) -> None:
        field = ConcatField("field", ["field_one", "field_two"])
        self.assertTrue("field_one_field_two", field.get_annotate())
        field = ConcatField("field", ["field_one__element", "field__other"])
        self.assertTrue("field_one_element_field_other", field.get_annotate())
        field = ConcatField(
            "field",
            ["field_one", "field_two"],
            target_field_name="field_annotate",
        )
        self.assertIn("field_annotate", field.get_annotate())

    def test_get_query(self) -> None:
        field = ConcatField("field", ["field_one", "field_two"])
        query = field.get_query("value")
        self.assertEqual(str(query), str(Q(_field="value")))
        field = ConcatField("field", ["field_one", "field_two"], lookup="icontains")
        query = field.get_query("value")
        self.assertEqual(str(query), str(Q(_field__icontains="value")))


class DateFieldTests(TestCase):
    def test_validate(self) -> None:
        field = DateField("field")

        errors, value = field.perform_validation("2020-12-31")
        self.assertEqual(len(errors), 0, errors)
        self.assertEqual(value, datetime.date(year=2020, month=12, day=31))

        errors, value = field.perform_validation("2020-12-12T10:25:30Z")
        self.assertNotEqual(len(errors), 0, "Expected errors")
        self.assertEqual(errors[0].code, "wrong_format")

        errors, value = field.perform_validation("31-12-2020")
        self.assertNotEqual(len(errors), 0, "Expected errors")
        self.assertEqual(errors[0].code, "wrong_format")


class DateTimeFieldTests(TestCase):
    def test_validate(self) -> None:
        field = DateTimeField("field")

        errors, value = field.perform_validation("2020-1-1T10:25:30Z")
        self.assertEqual(len(errors), 0, errors)
        self.assertEqual(
            value,
            datetime.datetime(
                year=2020,
                month=1,
                day=1,
                hour=10,
                minute=25,
                second=30,
                tzinfo=ZoneInfo("America/Phoenix"),
            ),
        )

        errors, value = field.perform_validation("2021-30-12")
        self.assertNotEqual(len(errors), 0, "Expected errors")
        self.assertEqual(errors[0].code, "wrong_format")

        errors, value = field.perform_validation("31-12-2020T10:10:10")
        self.assertNotEqual(len(errors), 0, "Expected errors")
        self.assertEqual(errors[0].code, "wrong_format")

        field = DateTimeField("field", date_format="%Y-%m-%dT%H:%M:%S%z")
        errors, value = field.perform_validation("2020-1-1T10:25:30+0700")
        self.assertEqual(len(errors), 0, errors)
        self.assertEqual(
            value,
            datetime.datetime(
                year=2020,
                month=1,
                day=1,
                hour=10,
                minute=25,
                second=30,
                tzinfo=ZoneInfo("Asia/Bangkok"),
            ),
        )

    @override_settings(USE_TZ=True)
    def test_validate_forcing_timezone(self) -> None:
        field = DateTimeField("field")

        errors, value = field.perform_validation("2020-1-1T10:25:30Z")
        self.assertEqual(len(errors), 0, errors)
        _datetime = datetime.datetime(
            year=2020, month=1, day=1, hour=10, minute=25, second=30
        )

        self.assertNotEqual(value, _datetime)
        self.assertEqual(value, timezone.make_aware(_datetime, default_timezone()))


class TestingRangeMixin(TestCase):
    def validate(
        self,
        field_class: type[Range],
        values: Any,
        expect_true: bool = True,
        allow_empty: bool = True,
    ) -> None:
        field = field_class("field", allow_empty=allow_empty)
        errors, _ = field.perform_validation(values)
        if expect_true:
            self.assertFalse(errors, errors)
        else:
            self.assertTrue(errors, "Expected errors")

    def test_validate(self) -> None:
        field_classes: list[Any] = [
            RangeIntegerField,
            RangeFloatField,
            RangeDecimalField,
        ]

        for field_class in field_classes:
            self.validate(field_class, "1", False)
            self.validate(field_class, "1,10")
            self.validate(field_class, ",10")
            self.validate(field_class, "1,")
            self.validate(field_class, ",10", False, False)
            self.validate(field_class, "1,", False, False)

        self.validate(RangeDateField, "2020-1-1,2020-12-31")
        self.validate(RangeDateField, ",2020-12-31")
        self.validate(RangeDateField, "2020-1-1,")

    def get_validate_query(
        self, field_class: type[Range], left_value: Any, right_value: Any
    ) -> None:
        field = field_class("field", equal=False)
        errors, value = field.perform_validation(
            "{left},{right}".format(
                left=left_value,
                right=right_value,
            )
        )

        self.assertEqual(len(errors), 0, errors)
        self.assertEqual(
            str(field.get_query(value)),
            str(Q(**{"field__gt": left_value, "field__lt": right_value})),
        )

        field = field_class("field", equal=True)
        errors, value = field.perform_validation(
            "{left},{right}".format(
                left=left_value,
                right=right_value,
            )
        )
        self.assertEqual(len(errors), 0, errors)
        self.assertEqual(
            str(field.get_query(value)),
            str(Q(**{"field__gte": left_value, "field__lte": right_value})),
        )

    def test_get_query(self) -> None:
        self.get_validate_query(RangeIntegerField, 1, 10)
        self.get_validate_query(RangeFloatField, 1.0, 10.0)
        self.get_validate_query(RangeDecimalField, Decimal(1), Decimal(10))


class TestingInMixin(TestCase):
    choices = [
        ("10", "uno"),
        ("20", "dos"),
        ("30", "tres"),
    ]

    def validate(self, field: Field, values: Any, is_true: bool = True) -> None:
        errors, _ = field.perform_validation(values)
        if is_true:
            self.assertEqual(len(errors), 0, errors)
        else:
            self.assertNotEqual(len(errors), 0, "Expected errors")

    def test_validate(self) -> None:
        field_integer = InIntegerField("field")
        self.validate(field_integer, "1,10,40")
        self.validate(field_integer, ",10")
        self.validate(field_integer, "1,")
        self.validate(field_integer, "1")

        field_choices = InChoicesField("field", choices=self.choices)
        self.validate(field_choices, "10,20")
        self.validate(field_choices, "10,20,30")
        self.validate(field_choices, "10")
        self.validate(field_choices, "10,50", False)
        self.validate(field_choices, "0,50", False)

    def test_get_query(self) -> None:
        field_integer = InIntegerField("field")
        errors, value = field_integer.perform_validation("9,7,5,4,3")

        self.assertEqual(len(errors), 0, errors)
        self.assertEqual(
            str(field_integer.get_query(value)),
            str(Q(**{"field__in": [9, 7, 5, 4, 3]})),
        )

        field_choices = InChoicesField("field", choices=self.choices)
        errors, value = field_choices.perform_validation("10,20")
        self.assertEqual(len(errors), 0, errors)
        self.assertEqual(
            str(field_choices.get_query(value)),
            str(Q(**{"field__in": ["uno", "dos"]})),
        )
