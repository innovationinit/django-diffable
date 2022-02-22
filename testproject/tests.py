# -*- coding: utf-8 -*-
from __future__ import (
    absolute_import,
    unicode_literals,
)

import copy
import pickle
from contextlib import contextmanager
from datetime import timedelta

import six
from diffable.models import DEFERRED
from freezegun import freeze_time
from six.moves import cPickle

from django.test.testcases import TestCase
from django.test.utils import override_settings
from django.utils import timezone

from diffable.models import DiffableModel

from testapp.models import (
    Author,
    Book,
    OldBook,
)


class DiffableModelTestCase(TestCase):

    def setUp(self):
        self.author = Author.objects.create(
            first_name='Ernest',
            last_name='Hemingway',
        )
        self.book = Book.objects.create(
            title='The Old Man and the Sea',
            author=self.author,
            publication_date=timezone.now().date(),
        )
        self.old_book = OldBook.objects.create(
            title='The Old Man and the Sea',
            author=self.author,
            publication_date=timezone.now().date(),
            age=12,
        )

    @override_settings(DIFFABLE_MODEL_SAVE_ONLY_CHANGES=True)
    def test_saving__unchanged_model__save_only_changes_on(self):
        with self.assertNumQueries(0):
            self.author.save()

    @override_settings(DIFFABLE_MODEL_SAVE_ONLY_CHANGES=True)
    def test_saving__unchanged_model_with_auto_now__save_only_changes_on(self):
        updated_at = self.book.updated_at

        with self.assertNumQueries(1), freeze_time(updated_at + timedelta(hours=1)):
            self.book.save()

        self.book.refresh_from_db()
        self.assertNotEqual(updated_at, self.book.updated_at)

    @override_settings(DIFFABLE_MODEL_SAVE_ONLY_CHANGES=True)
    def test_saving__unchanged_model_with_auto_now_in_table_inheritance__save_only_changes_on(self):
        updated_at = self.old_book.updated_at

        with self.assertNumQueries(1), freeze_time(updated_at + timedelta(hours=1)):
            self.old_book.save()

        self.old_book.refresh_from_db()
        self.assertNotEqual(updated_at, self.old_book.updated_at)

    @override_settings(DIFFABLE_MODEL_SAVE_ONLY_CHANGES=True)
    def test_saving__unchanged_model_with_deferred_fields__save_only_changes_on(self):
        author = Author.objects.only('last_name').get(pk=self.author.pk)

        with self.assertNumQueries(0):
            author.save()

        author.refresh_from_db()

        # Resolve deferred
        self.assertEqual('Ernest', author.first_name)

        with self.assertNumQueries(0):
            author.save()

    @override_settings(DIFFABLE_MODEL_SAVE_ONLY_CHANGES=True)
    def test_saving__changed_model__save_only_changes_on(self):
        first_name = self.author.first_name
        self.author.first_name = 'Mark'

        with self.assertNumQueries(1):
            self.author.save()

        self.author.refresh_from_db()
        self.assertNotEqual(first_name, self.author.first_name)

    @override_settings(DIFFABLE_MODEL_SAVE_ONLY_CHANGES=True)
    def test_saving__changed_model_with_auto_now__save_only_changes_on(self):
        updated_at = self.book.updated_at
        title = self.book.title
        self.book.title = 'The Lord of the Rings'

        with self.assertNumQueries(1), freeze_time(updated_at + timedelta(hours=1)):
            self.book.save()

        self.book.refresh_from_db()
        self.assertNotEqual(updated_at, self.book.updated_at)
        self.assertNotEqual(title, self.book.title)

    @override_settings(DIFFABLE_MODEL_SAVE_ONLY_CHANGES=True)
    def test_saving__changed_model_with_auto_now_in_table_inheritance__save_only_changes_on(self):
        updated_at = self.old_book.updated_at
        age = self.old_book.age
        self.old_book.age = 25

        with self.assertNumQueries(2), freeze_time(updated_at + timedelta(hours=1)):
            self.old_book.save()

        self.old_book.refresh_from_db()
        self.assertNotEqual(updated_at, self.old_book.updated_at)
        self.assertNotEqual(age, self.old_book.age)

    @override_settings(DIFFABLE_MODEL_SAVE_ONLY_CHANGES=True)
    def test_saving__changed_model_with_deferred_fields__save_only_changes_on(self):
        author = Author.objects.only('last_name').get(pk=self.author.pk)

        first_name = author.first_name
        author.first_name = 'Mark'

        with self.assertNumQueries(1):
            author.save()

        author.refresh_from_db()
        self.assertNotEqual(first_name, author.first_name)

    @override_settings(DIFFABLE_MODEL_SAVE_ONLY_CHANGES=False)
    def test_saving__unchanged_model__save_only_changes_off(self):
        with self.assertNumQueries(1):
            self.author.save()

    @override_settings(DIFFABLE_MODEL_SAVE_ONLY_CHANGES=False)
    def test_saving__changed_model__save_only_changes_off(self):
        first_name = self.author.first_name
        self.author.first_name = 'Mark'

        with self.assertNumQueries(1):
            self.author.save()

        self.author.refresh_from_db()
        self.assertNotEqual(first_name, self.author.first_name)

    def test_detecting_changes(self):
        book = Book.objects.get(pk=self.book.pk)

        self.assertFalse(book.has_changed)

        book.title = 'The Lord of the Rings'
        book.author = Author.objects.create(first_name='John', last_name='Tolkien')
        book.publication_date = timezone.now() + timedelta(days=20)

        self.assertTrue(book.has_changed)
        self.assertSetEqual({'title', 'author', 'publication_date'}, set(book.changed_fields))

        self.assertDictEqual(
            book.diff,
            {
                'title':    (self.book.title, book.title),
                'author': (self.book.author_id, book.author_id),
                'publication_date': (self.book.publication_date, book.publication_date),
            }
        )

    def test_detecting_changes__with_deferred(self):
        book = Book.objects.only('id').get(pk=self.book.pk)
        new_author = Author.objects.create(first_name='John', last_name='Tolkien')

        self.assertFalse(book.has_changed)

        # Resolve deferred
        assert book.title
        assert book.author
        assert book.publication_date

        # Check if resolving is treated as change
        self.assertFalse(book.has_changed)

        book = Book.objects.only('id').get(pk=self.book.pk)

        book.title = 'The Lord of the Rings'
        book.author = new_author
        book.publication_date = timezone.now() + timedelta(days=20)

        self.assertTrue(book.has_changed)
        self.assertSetEqual({'title', 'author', 'publication_date'}, set(book.changed_fields))

        self.assertDictEqual(
            book.diff,
            {
                'title': (DEFERRED, book.title),
                'author': (DEFERRED, book.author_id),
                'publication_date': (DEFERRED, book.publication_date),
            }
        )

        book.refresh_from_db(fields=['title', 'author'])
        book.author = new_author

        self.assertTrue(book.has_changed)
        self.assertSetEqual({'author', 'publication_date'}, set(book.changed_fields))

        self.assertIsNone(book.get_field_diff('title'))

        self.assertDictEqual(
            book.diff,
            {
                'author': (self.author.id, new_author.id),
                'publication_date': (DEFERRED, book.publication_date),
            }
        )

    def test_copying_is_disabled(self):
        with self.assertRaises(Exception) as cm:
            copy.copy(self.book)
        self.assertEqual(cm.exception.args, ('Copying DiffableModel breaks tracking changes of its field values. Use deepcopy instead.', ))

    def test_deepcopying__unchanged_model(self):
        self.assertDictEqual(self.book.diff, {})
        copied = copy.deepcopy(self.book)
        self.assertIsNot(copied, self.book)
        self.assertEqual(copied.title, self.book.title)
        self.assertEqual(copied.diff, {})

    def test_deepcopying__changed_model(self):
        self.book.title = 'The Lord of the Rings'
        self.assertDictEqual(self.book.diff, {'title': ('The Old Man and the Sea', 'The Lord of the Rings')})
        copied = copy.deepcopy(self.book)
        self.assertIsNot(copied, self.book)
        self.assertEqual(copied.title, 'The Lord of the Rings')
        self.assertEqual(copied.diff, {})

    def test_deepcopied_is_deepcopyable(self):
        copied = copy.deepcopy(self.book)
        copied_again = copy.deepcopy(copied)
        self.assertEqual(copied_again.title, self.book.title)

    def test_pickling_and_unpickling__pickle(self):
        for pickling_tool in [pickle, cPickle]:
            with self.subTest(pickling_tool=pickling_tool):
                self.book.title = 'The Holy Bible'
                pickled = pickling_tool.dumps(self.book)
                unpickled = pickling_tool.loads(pickled)
                # check that the unpickled instance is aware of the changes
                self.assertDictEqual(unpickled.diff, {'title': ('The Old Man and the Sea', 'The Holy Bible')})
                # check that tracking changes works after unpickling
                unpickled.title = 'The Lord of the Rings'
                self.assertDictEqual(unpickled.diff, {'title': ('The Old Man and the Sea', 'The Lord of the Rings')})

    def test_deleting_instance(self):
        paulo_coelho = Author.objects.create(first_name='Paulo', last_name='Coelho')
        instance_id = id(paulo_coelho)
        self.assertIn(instance_id, DiffableModel._diff_locks)
        del paulo_coelho  # :)
        self.assertNotIn(instance_id, DiffableModel._diff_locks)

    def subTest(self, *args, **kwargs):
        if six.PY2:
            @contextmanager
            def nullcontext():
                yield

            return nullcontext()
        return super(DiffableModelTestCase, self).subTest(*args, **kwargs)
