# -*- coding: utf-8 -*-
"""Based on ModelDiffMixin, http://stackoverflow.com/a/13842223"""

from contextlib import contextmanager
from copy import deepcopy
from threading import Lock

from django.conf import settings
from django.db import models
from django.db.models.base import DEFERRED
from django.utils.functional import cached_property


class DiffableModel(models.Model):
    """An abstract model that tracks model fields' values and provide some useful api to know what fields have been changed."""

    _diff_locks = {}

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        super(DiffableModel, self).__init__(*args, **kwargs)
        self._initialize()

    def __del__(self):
        try:
            del self._diff_locks[id(self)]
        except KeyError:
            pass

    def __copy__(self):
        raise Exception('Copying DiffableModel breaks tracking changes of its field values. Use deepcopy instead.')

    def __getattribute__(self, item):
        if item == '__deepcopy__' and getattr(self, '_is_during_deepcopy', False):
            return None
        return super(DiffableModel, self).__getattribute__(item)

    def __deepcopy__(self, memo):
        try:
            self._is_during_deepcopy = True
            deepcopied = deepcopy(self, memo)
            del deepcopied._is_during_deepcopy
            deepcopied._initialize()
            return deepcopied
        finally:
            del self._is_during_deepcopy

    def __setstate__(self, state):
        """Initialize lock after unpickling."""
        super(DiffableModel, self).__setstate__(state)
        self._initialize_lock()

    def _initialize(self):
        self._initialize_lock()
        self._in_save_only_changes_context = False
        self.store_initial()

    def _initialize_lock(self):
        self._diff_lock = Lock()

    @property
    def _diff_lock(self):
        return self._diff_locks[id(self)]

    @_diff_lock.setter
    def _diff_lock(self, lock):
        self._diff_locks[id(self)] = lock

    def store_initial(self, fields=None):
        with self._diff_lock:
            if fields is None:
                self.__initial = self._dict
            elif len(fields) > 0:
                state = self._dict
                for field_name in fields:
                    field_name = field_name if field_name in self.__initial else self.field_attname_to_name.get(field_name)
                    if field_name:
                        self.__initial[field_name] = state[field_name]

    @property
    def diff(self):
        with self._diff_lock:
            try:
                d1 = self.__initial
            except AttributeError:
                raise RuntimeError(
                    'The initial state of the current model instance has not been saved automatically. '
                    'Use the store_initial() method before making changes to the instance.')
            d2 = self._dict
            diffs = [(k, (v, d2[k])) for k, v in d1.items() if v != d2[k]]
            return dict(diffs)

    @property
    def has_changed(self):
        return bool(self.diff)

    @property
    def changed_fields(self):
        return list(self.diff.keys())

    def get_field_diff(self, field_name):
        """Return a diff for field if it's changed and None otherwise."""
        return self.diff.get(field_name, None)

    def save(self, *args, **kwargs):
        """
        Save model and set initial state.
        If setting DIFFABLE_MODEL_SAVE_ONLY_CHANGES is set to True, save only changed fields. Default is False.
        """
        if not self._state.adding and getattr(settings, 'DIFFABLE_MODEL_SAVE_ONLY_CHANGES', False) and not kwargs.get('force_insert'):
            assert kwargs.get('update_fields') is None, \
                "If DIFFABLE_MODEL_SAVE_ONLY_CHANGES is set to True updated_fields shouldn't be supplied to save method!"

            with self.save_only_changes_context():
                super(DiffableModel, self).save(*args, **kwargs)

        else:
            super(DiffableModel, self).save(*args, **kwargs)

        self.store_initial()

    def _save_parents(self, cls, using, update_fields):
        if self._in_save_only_changes_context:
            update_fields = self._get_fields_for_update()

        super(DiffableModel, self)._save_parents(cls, using, update_fields)

    def _save_table(self, raw=False, cls=None, force_insert=False,
                    force_update=False, using=None, update_fields=None):
        if self._in_save_only_changes_context:
            update_fields = self._get_fields_for_update()

            if not update_fields:
                return 0

        return super(DiffableModel, self)._save_table(raw, cls, force_insert, force_update, using, update_fields)

    def refresh_from_db(self, using=None, fields=None, **kwargs):
        """Refresh model and set initial state."""
        super(DiffableModel, self).refresh_from_db(using=using, fields=fields, **kwargs)
        # Deferred fields are populated using refresh_from_db(fields=[field_name])
        self.store_initial(fields=fields)

    @property
    def _dict(self):
        deferred_fields = self.get_deferred_fields()
        data = {}
        for f in self._meta.fields:
            # Change in M2M isn't actually change on model
            if isinstance(f, models.ManyToManyField):
                continue

            if f.attname in deferred_fields:
                data[f.name] = DEFERRED
            else:
                data[f.name] = f.value_from_object(self)

        return data

    @property
    def fields_for_update(self):
        updated_fields = []

        for field in self._meta.fields:
            if getattr(field, 'auto_now', False):
                updated_fields.append(field.name)

        updated_fields.extend(self.changed_fields)

        return updated_fields

    @contextmanager
    def save_only_changes_context(self):
        try:
            self._cached_update_fields = None
            self._in_save_only_changes_context = True
            yield
        finally:
            del self._cached_update_fields
            self._in_save_only_changes_context = False

    @cached_property
    def field_attname_to_name(self):
        return {field.attname: field.name for field in self._meta.fields}

    def _get_fields_for_update(self):
        assert self._in_save_only_changes_context
        if not self._cached_update_fields:
            self._cached_update_fields = self.fields_for_update
        return self._cached_update_fields
