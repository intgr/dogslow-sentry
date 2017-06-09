#!/usr/bin/env python2.7

import os
import json
import subprocess
import sys
import urllib2
from textwrap import dedent

resp = urllib2.urlopen('https://pypi.python.org/pypi/dogslow/json')
version = (subprocess.check_output('python setup.py --version', shell=True)
                     .strip())
if version in json.load(resp)['releases']:
    print('Publishing failed: version %s already exists' % version)
    exit(1)
else:
    with open(os.path.join(os.environ['HOME'], '.pypirc'), 'w') as f:
        f.write(dedent("""\
            [distutils]
            index-servers =
                pypi
            
            [pypi]
            repository=https://upload.pypi.org/legacy/
            username: %(USERNAME)s
            password: %(PASSWORD)s
            """ % os.environ))
    exit(os.system('python setup.py sdist upload'))
