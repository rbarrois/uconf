#!/usr/bin/python
# -*- coding: utf-8 -*-

from distutils.core import setup

setup(name = 'confmgr',
        version = '0.1.0',
        description = 'Tool for managing config files',
        author = "Raphaël Barrois",
        author_email = "raphael.barrois@xelmail.com",
        url = "confmgr.xelnor.net",
        packages = ['confmgr'],
        requires = ['os', 're', 'difflib', 'hashlib', 'subprocess', 'optparse', 'shutils', 'ConfigParser'],
        scripts = ['bin/confmgr'],
        )