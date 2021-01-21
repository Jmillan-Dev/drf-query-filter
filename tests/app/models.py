from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=24)


class Author(models.Model):
    first_name = models.CharField(max_length=24)
    last_name = models.CharField(max_length=24)
    birthday = models.DateField()


class Book(models.Model):
    name = models.CharField(max_length=24)
    category = models.ForeignKey('Category', on_delete=models.SET_NULL, null=True)
    page_count = models.IntegerField()
    authors = models.ManyToManyField('Author')
    
    class Meta:
        default_related_name = 'books'
