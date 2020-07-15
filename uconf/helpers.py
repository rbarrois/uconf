# -*- coding: utf-8 -*-
# Copyright (c) 2010-2013 Raphaël Barrois
# This software is distributed under the two-clause BSD license.

import os
import socket


def filter_iter(iterator, items, key=lambda o: o, empty_is_all=False):
    """Filter items from an iterator, keeping only those in a set."""

    output_all = False
    if items:
        items = frozenset(items)
    elif empty_is_all:
        output_all = True

    for item in iterator:
        if output_all or key(item) in items:
            yield item


def flatten(fields, separator=None):
    """Flatten a list of space-separated names."""
    flattened = set()
    for field in fields:
        flattened |= set(field.split(separator))
    return flattened


def get_absolute_path(path, base=''):
    path = os.path.join(base, os.path.expanduser(path))
    return os.path.abspath(path)


def get_relative_path(root, path, base=''):
    """Converts the given 'path' to a path relative to the 'root'."""
    return os.path.relpath(get_absolute_path(path, base=base), root)


def get_hostnames(name=''):
    """Return the list of hostnames for a name (defaults to local host)."""
    fqdn = socket.getfqdn(name)
    return fqdn, fqdn.split('.')[0]
