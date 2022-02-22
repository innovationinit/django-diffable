# -*- coding: utf-8 -*-
import os
from setuptools import setup

with open(os.path.join(os.path.dirname(__file__), 'README.md')) as readme:
    README = readme.read()


def get_packages(package):
    """
    Return root package and all sub-packages.
    """
    return [dirpath
            for dirpath, dirnames, filenames in os.walk(package)
            if os.path.exists(os.path.join(dirpath, '__init__.py'))]


# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='django-diffable',
    version='1.0.0',
    packages=get_packages('diffable'),
    include_package_data=True,
    description='A model that tracks model fields\' values.',
    long_description=README,
    long_description_content_type='text/markdown',
    author='IIIT',
    author_email='github@iiit.pl',
    install_requires=[
        'Django>=2.0.0,<3.3',
    ],
    test_suite='testproject.runtests.run_tests',
    tests_require=[
        'freezegun>=0.3.9',
    ],
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
)
