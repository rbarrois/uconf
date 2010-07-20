#!/usr/bin/env python2.6
# -*- coding: utf-8 -*-

from distutils.core import setup

setup(name = 'confmgr',
        version = '@VERSION@',
        description = 'Tool for managing config files',
        author = "Raphaël Barrois",
        author_email = "raphael.barrois@xelmail.com",
        url = "http://confmgr.xelnor.net/",
        packages = ['confmgr'],
        requires = ['os', 're', 'difflib', 'hashlib', 'subprocess', 'optparse', 'shutils', 'ConfigParser'],
        scripts = ['bin/confmgr', 'bin/install-bin', 'bin/confmgr-bin'],
        )
