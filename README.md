# drf-query-filter

**drf-query-filter** is used to design fast and user pre defined queries with the 'query' found in the request url.

## Table of contents

* [Installation](#installation)
* [Usage](#usage)
    * [QuickStart](#quickstart)
    * [Fields](#fields)
* [How does it work?](#how-does-it-work)

## Installation

drf-query-filter can be installed using pip

```shell
pip install drf-query-filter
```

## Usage

### QuickStart

In `settings.py`:

```python
INSTALLED_APPS = [
    ...,
    'drf_query_filter',
    ...
]
```

In views:

```python
...
from rest_framework import viewsets
from drf_query_filter import fields, filters

...


class ExampleViewSet(viewsets.GenericViewSet[Any]):
    ...
    filter_backends = [filters.QueryParamFilter]

    query_param = [
        fields.StringField('id', 'id') & fields.StringField('user_id', 'user__id'),
        fields.RangeDateTimeField('date_created', 'element__date_created'),
    ]
```

### Fields

The view requires the definition the fields to be used in the filter. There are two ways of doing this.  

#### By attribute:

```python
query_params = [
    fields.StringField('id') & fields.StringField('username', 'username__icontains'),
    fields.ConcatField('full_name', ['first_name', V(' '), 'last_name'])
]
```

#### By callable:

```python
def get_query_params(self) -> list[Node]:
    return [
        fields.StringField('id') & fields.StringField('username', 'username__icontains'),
        fields.ConcatField('full_name', ['first_name', V(' '), 'last_name'])
    ]
```

The first value of the Field constructor is the name of the query in the request. For example:

> `/path/to/somewhere/?username=value`

With the query parameter **target_fields** of the Field one can tell which are the target fields of the model.

Not assigning the **target_field** will assume that the name of the field is the same for the name of the target field.

```python
fields.StringField('username')  # it will user `username` as the target field.
``` 

To tell what **target_field** it is use the param **target_fields**,
using only a str will target only one field in the model.

```python
fields.StringField('search', 'username')
```

Using a list or a tuple will target multiple fields of the model.

```python
fields.StringField('search', ['username', 'first_name', 'last_name'], connector=Q.OR)
```

Meaning that the result in the field `search` *(in this case)* will be assigned to all the target fields.

### How does it work?

With the following fields arraigned like this:

```python
query_params = [
    fields.Field('id') & fields.Field('username', 'user__username__icontains'),
    fields.RangeDateTimeField('date_created', equal=True) | fields.BooleanField('vip', 'vip_status'),
    fields.ConcatField('full_name', ['user__first_name', V(' '), 'user__last_name'], lookup='icontains'),
]
```

Is equivalent to the following lines of code: *(if all values are found in the request)*:

```python
queryset = queryset.filter(
  Q(id=f'{query_params["id"]}') &
  Q(user__username__icontains=f'{request.query_params["username"]}')
)
queryset = queryset.filter(
  Q(
    date_created__gte=f'{request.query_params["date_created"]}',
    date_created__lte=f'{request.query_params["date_created"]}'
  ) | Q(vip_status=f'{request.query_params["vip"]}')
)

queryset = queryset.annotate(
  first_name_last_name=Concat('user__first_name', V(' '), 'user__last_name')
).filter(
  Q(first_name_last_name__icontains=f'{request.query_params["full_name"]}')
)
```
