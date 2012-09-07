# coding: utf-8
# Copyright (c) 2010-2012 Raphaël Barrois

"""Abstract the filesystem layer."""

import io
import os
import stat


class FileSystem(object):
    def __init__(self, fs):
        self.fs = fs

    def __getattr__(self, name):
        return getattr(self.fs, name)

    def open(self, filename, mode='r', encoding=None, **kwargs):
        base_file = self.fs.open(filename, mode, **kwargs)
        if 't' in mode:
            return io.open(base_file, encoding=encoding or self.encoding)
        else:
            return base_file

    def read_one_line(self, filename, encoding=None):
        """Read one (stripped) line from a file.

        Typically used to read a password.
        """
        with self.open(filename, 'rt', **kwargs) as f:
            return f.readline().strip()

    def readlines(self, filename, encoding=None):
        """Read all lines from a file.

        Yields lines of the file, stripping the terminating \n.
        """
        with self.open(filename, 'rt', **kwargs) as f:
            for line in f:
                if line and line[-1] == '\n':
                    # Strip final \n
                    line = line[:-1]
                yield line

    def writelines(self, filename, lines, encoding=None):
        """Write a set of lines to a file.

        A \n will be appended to lines.
        """
        with self.open(filename, 'wt', encoding=encoding) as f:
            for line in lines:
                f.write(line)
                # Add final \n.
                f.write('\n')

    # Complex commands
    def create_symlink(self, link_name, target, relative=False, force=False):
        if self.access(link_name):
            file_stat = self.stat(link_name)
            if not stat.S_ISLNK(file_stat.st_mode) and not force:
                raise IOError(
                    "File at %s exists and is not a symlink." % link_name)
            elif stat.S_ISDIR(file_stat.st_mode):
                raise IOError("%s exists and is a directory.")
            else:
                self.remove(link_name)

        # TODO: Handle relative=True
        self.symlink(link_name, target)
