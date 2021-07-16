#!/usr/bin/env python3
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
    python_requires=">=3.7",
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
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
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
    install_requires=["django>=2.2", "sentry-sdk>=1.0"],
    version="2.0",
)
