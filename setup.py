#!/usr/bin/env python

import os
import sys

import salesforce

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

if sys.argv[-1] == 'publish':
    os.system('python setup.py sdist upload')
    sys.exit()

packages = [
    'salesforce',
    'salesforce.metadata',
    'salesforce.metadata.v30',
    'salesforce.rest',
    'salesforce.soap',
    'salesforce.soap.v29',
]

requires = [
    'anyjson>=0.3.3',
    'requests>=2.3.0',
    'pytz>=2014.3',
    'suds-jurko>=0.6',
    'wrapt>=1.8.0',
]

with open('README.rst') as f:
    readme = f.read()
with open('LICENSE') as f:
    license = f.read()

setup(
    name='salesforce',
    version=salesforce.__version__,
    description='A set of Python client libraries for Salesforce APIs',
    long_description=readme,
    author='David Gouldin',
    author_email='dgouldin@heroku.com',
    url='https://github.com/heroku/python-salesforce-client',
    packages=packages,
    package_data={'': ['LICENSE']},
    package_dir={'salesforce': 'salesforce'},
    include_package_data=True,
    install_requires=requires,
    license=license,
    zip_safe=False,
    classifiers=(
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
    ),
)
