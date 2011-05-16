#!/usr/bin/env python
"""Installs cram"""

import os
import sys
from distutils.core import setup

def long_description():
    """Get the long description from the README"""
    return open(os.path.join(sys.path[0], 'README.txt')).read()

setup(
    author='Erik van Zijst',
    author_email='erik.van.zijst@gmail.com',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Utilities',
    ],
    description='A Django middleware that logs tracebacks of slow requests.',
    download_url='https://bitbucket.org/evzijst/django_watchdog/django_watchdog-0.1.tar.gz',
    keywords='django debug watchdog middleware',
    license='GNU LGPL',
    long_description=long_description(),
    name='django_watchdog',
    py_modules=['django_watchdog'],
    url='https://bitbucket.org/evzijst/django_watchdog',
    version='0.1',
)
