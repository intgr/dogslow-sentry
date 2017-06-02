#!/usr/bin/env python

import os
import json
import subprocess
import sys
import urllib2

resp = urllib2.urlopen('https://pypi.python.org/pypi/dogslow/json')
version = (subprocess.check_output('python setup.py --version', shell=True)
                     .strip())
if version in json.load(resp)['releases']:
    print('Publishing failed: version %s already exists' % version)
    exit(1)
else:
    exit(os.system('echo python setup.py dist upload'))
