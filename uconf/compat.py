# -*- coding: utf-8 -*-
# Copyright (c) 2010-2013 Raphaël Barrois
# This software is distributed under the two-clause BSD license.

from __future__ import unicode_literals, absolute_import

"""Py2 backwards compatibility fixes."""

import sys

PY2 = sys.version_info[0] < 3

if PY2:
    text_types = (str, unicode)
else:
    text_types = (str,)
