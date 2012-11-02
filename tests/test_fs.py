#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2012 Raphaël Barrois
# This software is distributed under the two-clause BSD license.


import io
import functools
import os
import tempfile
import unittest

from fs import osfs

from uconf import fs


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
        self.fs = fs.FileSystem('/')

    @with_tempfile
    def test_read_line(self, name):
        with io.open(name, 'wt', encoding='utf8') as f:
            f.write(u"  Example line\n<blank> \n")

        self.assertEqual(u"Example line", self.fs.read_one_line(name))

    @with_tempfile
    def test_read_line_utf8(self, name):
        with io.open(name, 'wt', encoding='utf8') as f:
            f.write(u"yüþæó, ßøḿē ūñįçØðe")

        self.assertEqual(u"yüþæó, ßøḿē ūñįçØðe", self.fs.read_one_line(name, 'utf8'))

    @with_tempfile
    def test_read_line_latin1(self, name):
        with io.open(name, 'wt', encoding='latin1') as f:
            f.write(u"À lïttlè látîñ1")

        self.assertEqual(u"À lïttlè látîñ1", self.fs.read_one_line(name, 'latin1'))

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

    @with_tempfile
    def test_write_utf8(self, name):
        self.fs.writelines(name, [u"yüþæó, ßøḿē ūñįçØðe"], 'utf8')
        with io.open(name, 'rt', encoding='utf8') as f:
            self.assertEqual(u"yüþæó, ßøḿē ūñįçØðe\n", f.readline())

    @with_tempfile
    def test_write_latin1(self, name):
        self.fs.writelines(name, [u"À lïttlè látîñ1"], 'latin1')
        with io.open(name, 'rt', encoding='latin1') as f:
            self.assertEqual(u"À lïttlè látîñ1\n", f.readline())


if __name__ == '__main__':
    unittest.main()
