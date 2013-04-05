#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2010-2013 Raphaël Barrois
# This software is distributed under the two-clause BSD license.

import os
import re
import sys

from distutils.core import setup
from distutils import cmd

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


def read_requirements(filename):
    dep_re = re.compile(r'^([\w_-]+)((?:>=|<=|==|!=).*)?$')
    with open(filename, 'rt') as f:
        lines = [l.strip() for l in f]
    lines = [l for l in lines if l and not l.startswith('#')]

    deps = []

    for line in lines:
        match = dep_re.match(line)
        if not match:
            raise ValueError("Invalid dependency line %r in %s" % (line, filename))
        dep, v = match.groups()
        if v:
            deps.append('%s (%s)' % (dep, v))
        else:
            deps.append(dep)
    return deps


class test(cmd.Command):
    """Run the tests for this package."""
    command_name = 'test'
    description = 'run the tests associated with the package'

    user_options = [
        ('test-suite=', None, "A test suite to run (defaults to 'tests')"),
    ]

    def initialize_options(self):
        self.test_runner = None
        self.test_suite = None

    def finalize_options(self):
        self.ensure_string('test_suite', 'tests')

    def run(self):
        """Run the test suite."""
        try:
            import unittest2 as unittest
        except ImportError:
            import unittest

        if self.verbose:
            verbosity=1
        else:
            verbosity=0

        loader = unittest.TestLoader()
        suite = unittest.TestSuite()

        if self.test_suite == 'tests':
            for test_module in loader.discover('.'):
                suite.addTest(test_module)
        else:
            suite.addTest(loader.loadTestsFromName(self.test_suite))

        result = unittest.TextTestRunner(verbosity=verbosity).run(suite)
        if not result.wasSuccessful():
            sys.exit(1)


PACKAGE = 'uconf'


setup(
    name=PACKAGE,
    version=get_version(PACKAGE),
    author="Raphaël Barrois",
    author_email="raphael.barrois+@polytechnique.org",
    description='UConf, a smart tool for managing config files',
    license="BSD",
    keywords=['configuration', 'management', 'uconf', 'confmgr', 'config'],
    url="http://uconf.xelnor.net/",
    packages=[PACKAGE],
    scripts=['bin/uconf'],
    requires=read_requirements('requirements.txt'),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: BSD License",
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 2 :: Only",
        "Topic :: System :: Installation/Setup",
        "Topic :: System :: Systems Administration",
    ],
    cmdclass={'test': test},
)
