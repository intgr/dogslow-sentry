#!/usr/bin/env python
# Installs dogslow.

import os
import sys
from setuptools import setup


def long_description():
    """Get the long description from the README"""
    return open(os.path.join(sys.path[0], "README.rst")).read()


setup(
    author="Marti Raudsepp",
    author_email="marti@juffo.org",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Framework :: Django",
        "Intended Audience :: Developers",
        (
            "License :: OSI Approved :: "
            "GNU Library or Lesser General Public License (LGPL)"
        ),
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Topic :: Software Development :: Debuggers",
        "Topic :: Utilities",
    ],
    description="A Django middleware that logs tracebacks of slow requests to Sentry.",
    keywords="django debug watchdog middleware traceback sentry",
    license="GNU LGPL",
    long_description=long_description(),
    name="dogslow-sentry",
    packages=["dogslow_sentry"],
    url="https://bitbucket.org/evzijst/dogslow",
    install_requires=["django"],
    extras_require={
        "sentry": ["sentry_sdk"],
    },
    version="2.0",
)
