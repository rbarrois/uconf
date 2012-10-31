# coding: utf-8
# Copyright (c) 2010-2012 Raphaël Barrois

from __future__ import unicode_literals, absolute_import

from fs import mountfs
import os


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


def get_absolute_path(path, base=''):
    path = os.path.join(base, os.path.expanduser(path))
    return os.path.abspath(path)


def rebase_fs(base, filesystem):
    mounted_fs = mountfs.MountFS()
    mounted_fs.mount(base, filesystem)
    return mounted_fs


def get_relative_path(root, path, base=''):
    """Converts the given 'path' to a path relative to the 'root'."""
    return os.path.relpath(get_absolute_path(path, base=base), root)
