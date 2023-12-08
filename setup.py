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
        "Development Status :: 6 - Mature",
        "Framework :: Django",
        "Framework :: Django :: 2.2",
        "Framework :: Django :: 3.0",
        "Framework :: Django :: 3.2",
        "Framework :: Django :: 3.2",
        "Framework :: Django :: 4.0",
        "Framework :: Django :: 4.1",
        "Framework :: Django :: 4.2",
        "Framework :: Django :: 5.0",
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
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Debuggers",
        "Topic :: Utilities",
    ],
    description="A Django middleware that logs tracebacks of slow requests to Sentry.",
    keywords="django debug watchdog middleware traceback sentry",
    license="GNU LGPL",
    long_description=long_description(),
    long_description_content_type="text/x-rst",
    name="dogslow-sentry",
    packages=["dogslow_sentry"],
    url="https://github.com/intgr/dogslow-sentry",
    project_urls={
        "Release notes": "https://github.com/intgr/dogslow-sentry/blob/main/README.rst#changelog",
    },
    install_requires=["django>=2.2", "sentry-sdk>=1.0"],
    version="2.0.1",
)
