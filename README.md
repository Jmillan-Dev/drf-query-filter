# drf-query-filter

**drf-query-filter** is used to design fast and complex queries with the 'query' found in the request url.

## Table of contents

* [Installation](#installation)
* [Usage](#usage)
    * [QuickStart](#quickstart)
    * [Fields](#fields)
* [How does it work?](#how-does-it-work)

## Installation

drf-query-filter can be installed using pip

```shell
pip3 install drf-query-filter
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


class ExampleViewSet(viewsets.GenericViewSet):
    ...
    filter_backends = [filters.QueryParamFilter, ]
    
    query_param = [
        fields.Field('id', 'id') & fields.Field('user_id', 'user__id'),
        fields.RangeDateTimeField('date_created', 'element__date_created'),
    ]

```

### Fields

the view needs to define the fields to be used in the query set. there are two ways of doing this.  
by attribute:

```python
query_param = [
    fields.Field('id') & fields.Field('username', 'username__icontains'),
    fields.ConcatField('full_name', ['first_name', V(' '), 'last_name'])
]
```

or by a callable:

```python
def get_query_param(self):
    return [
        fields.Field('id') & fields.Field('username', 'username__icontains'),
        fields.ConcatField('full_name', ['first_name', V(' '), 'last_name'])
    ]
```

The first value of the Field constructor is the name of the query that it will look for in the request. meaning that in
the case of using `fields.Field('username')` it will try to search for the key *'username'* in the query:

> http://localhost/path/to/somewhere/? **username** =value

With the param **target_fields** of the Field one can tell which are the target fields of the model.

Not assigning the **target_field** will assume that the name of the field is the same for the name of the target field.

```python
fields.Field('username')  # it will user `username` as the target field.
``` 

To tell what **target_field** it is use the param **target_fields**,
using only a str will target only one field in the model.

```python
fields.Field('search', 'username')
```

Using a list or a tuple will target multiple fields of the model.

```python
fields.Field('search', ['username', 'first_name', 'last_name'])
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
queryset = queryset.filter(Q(id='value') & Q(user__username__icontains='value'))
queryset = queryset.filter(Q(date_created__gte='value', date_created__lte='value') | Q(vip_status='value'))

queryset = queryset\
    .annotate(first_name_last_name=Concat('user__first_name', V(' '), 'user__last_name'))\
    .filter(Q(first_name_last_name__icontains='value'))
```

If some values are not found in the request, they are ignored, for example:

If the request doesn't contain `full_name` it will ignore the last field (the **annotate** and **filter**), 
And instead it will only do the first two.

**Request:** `/?id=9&username=value&date_created=2021-1-1,2021-12-31&vip=true`

```python
queryset = queryset.filter(Q(id=9) & Q(user__username__icontains='value'))
queryset = queryset.filter(Q(date_created__gte=datetime(year=2021, month=1, day=1),
                             date_created__lte=datetime(year=2021, month=12, day=1)) |
                           Q(vip_status=True))
```

Another example where we only ask for the *id* and *full_name*:

**Request:** `/?id=10&full_name=Something+Something`

```python
queryset = queryset.filter(Q(id=10))

queryset = queryset\
    .annotate(first_name_last_name=Concat('user__first_name', V(' '), 'user__last_name'))\
    .filter(Q(first_name_last_name__icontains='Something Something'))
```
