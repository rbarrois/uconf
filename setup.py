#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
import os
import re

root_dir = os.path.abspath(os.path.dirname(__file__))


def get_version(package_name):
    version_re = re.compile(r"^__version__ = [\"']([\w_.-]+)[\"']$")
    package_components = package_name.split('.')
    path_components = package_components + ['__init__.py']
    with open(os.path.join(root_dir, *path_components)) as f:
        for line in f:
            match = version_re.match(line[:-1])
            if match:
                return match.groups()[0]
    return '0.1.0'


PACKAGE = 'confmgr'


setup(
    name=PACKAGE,
    version=get_version(PACKAGE),
    author="Raphaël Barrois",
    author_email="raphael.barrois@polytechnique.org",
    description='ConfMgr, a smart tool for managing config files',
    license="MIT",
    keywords=['configuration', 'management', 'confmgr', 'config'],
    url="http://confmgr.xelnor.net/",
    packages=find_packages(),
    scripts=['bin/confmgr', 'bin/install-bin', 'bin/confmgr-bin'],
    setup_requires=[
        'distribute',
    ],
    install_requires=[
        'tdparser',
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
    test_suite='tests',
)
