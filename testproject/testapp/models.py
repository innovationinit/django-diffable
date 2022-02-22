from django.db import models

from diffable.models import DiffableModel


class Author(DiffableModel):

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)


class Book(DiffableModel):
    """Testing auto_now and relations"""

    title = models.CharField(max_length=100)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    publication_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class OldBook(Book):
    """Just to test table inheritance"""

    age = models.PositiveIntegerField()
