#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2012 Raphaël Barrois


import io
import functools
import os
import tempfile
import unittest

from confmgr import fs


def with_tempfile(fun):
    """Decorator providing a temporary file name to the decorated method.

    The tempfile will be created before calling the function, and unlinked
    once it returns (or fails).

    If will be provided as an extra 'name' positional argument.
    """
    @functools.wraps(fun)
    def decorated(self, *args, **kwargs):
        fd, name = tempfile.mkstemp()
        os.close(fd)
        try:
            return fun(self, name, *args, **kwargs)
        finally:
            os.unlink(name)
    return decorated


class FileSystemTestCase(unittest.TestCase):
    """Tests for a 'normal' file system."""
    def setUp(self):
        self.fs = fs.FileSystem(root='/')

    @with_tempfile
    def test_read_line(self, name):
        with io.open(name, 'wt', encoding='utf8') as f:
            f.write(u"  Example line\n<blank> \n")

        self.assertEqual(u"Example line", self.fs.read_one_line(name))

    @with_tempfile
    def test_read_lines(self, name):
        with io.open(name, 'wt', encoding='utf8') as f:
            f.write(u"  Example line\n<blank> \n")

        self.assertEqual([
            u"  Example line",
            u"<blank> ",
        ], list(self.fs.readlines(name)))

    @with_tempfile
    def test_writing(self, name):
        self.fs.writelines(name, [
            u"  Example line",
            u"<blank> \n",
            u"final.",
            ])

        with io.open(name, 'rt', encoding='utf8') as f:
            lines = [line for line in f]

        self.assertEqual([
            u"  Example line\n",
            u"<blank> \n",
            u"\n",
            u"final.\n",
        ], lines)


class ReadOnlyFSTestCase(unittest.TestCase):
    def setUp(self):
        self.fs = fs.ReadOnlyFS(root='/')

    @with_tempfile
    def test_read_line(self, name):
        with io.open(name, 'wt', encoding='utf8') as f:
            f.write(u"  Example line\n<blank> \n")

        self.assertEqual(u"Example line", self.fs.read_one_line(name))

    @with_tempfile
    def test_read_lines(self, name):
        with io.open(name, 'wt', encoding='utf8') as f:
            f.write(u"  Example line\n<blank> \n")

        self.assertEqual([
            u"  Example line",
            u"<blank> ",
        ], list(self.fs.readlines(name)))

    @with_tempfile
    def test_writing_fails(self, name):
        with io.open(name, 'wt', encoding='utf8') as f:
            f.write(u"  Example line\n<blank> \n")

        self.assertRaises(IOError, self.fs.writelines, name, [])


if __name__ == '__main__':
    unittest.main()
