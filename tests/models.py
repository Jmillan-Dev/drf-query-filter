from django.db import models


class BasicModel(models.Model):
    string_uno = models.CharField(max_length=255)  # type: ignore
    string_dos = models.CharField(max_length=255)  # type: ignore
    date = models.DateField()  # type: ignore
    integer = models.IntegerField()  # type: ignore
    boolean = models.BooleanField()  # type: ignore
