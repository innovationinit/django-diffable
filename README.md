# Django Diffable

![example workflow](https://github.com/innovationinit/django-diffable/actions/workflows/test-package.yml/badge.svg?branch=main)
[![Coverage Status](https://coveralls.io/repos/github/innovationinit/django-diffable/badge.svg)](https://coveralls.io/github/innovationinit/django-diffable)


## About

A django abstract model that tracks model fields' values and provide some useful api to know what fields have been changed.

## Install

```bash
pip install django-diffable
```

## Usage

Inherit from _DiffableModel_:

```python
from diffable.models import DiffableModel
from django.db import models


class Product(DiffableModel):
    name = models.CharField(max_length=30)
```

Use as follows:

```python
>>> product = Product(name='Atari')
>>> product.has_changed
False
>>> product.changed_fields
[]
>>> product.name = 'Commodore'
>>> product.has_changed
True
>>> product.changed_fields
['name']
>>> product.diff
{'name': ('Atari', 'Commodore')}
>>> product.get_field_diff('name')
('Atari', 'Commodore')
>>> product.save()
>>> product.has_changed
False
>>> product.name = 'ZX Spectrum'
>>> product.has_changed
True
>>> product.refresh_from_db()
>>> product.has_changed
False
>>> product.name
'Commodore'
```

## License
The Django Wicked Historian package is licensed under the [FreeBSD
License](https://opensource.org/licenses/BSD-2-Clause).
