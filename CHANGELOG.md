# Changelog for drf-query-filter

## 0.2.0

* Added support for Django 6.0
* Added typing to the project
* Removed support for Python 3.11
* Internal logic for Field has been reworked
* Added support for Xor in Fields
* Added new field "ListField"
* Added new field "StringField", It allows schema_format to be defined for documentation purposes
* BooleanField now lowers the string case of the raw input
* ChoicesField now uses rest_framework's functions to deal with choices
* DecimalField now checks for "nan", "inf" or "-inf" values
