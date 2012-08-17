# coding: utf-8
# Copyright (c) 2010-2012 Raphaël Barrois

"""Abstract the filesystem layer."""

import io
import os

class BaseFileSystem(object):
    """Abstraction layer around the file system.

    All files are expected to be UTF8-encoded.
    """
    def __init__(self, root, encoding='utf8'):
        self.root = root
        self.encoding = encoding

    def open(self, filename, mode):
        raise NotImplementedError()

    def read_one_line(self, filename):
        """Read one (stripped) line from a file.

        Typically used to read a password.
        """
        with self.open(filename, 'r') as f:
            return f.readline().strip()

    def readlines(self, filename):
        """Read all lines from a file.

        Yields lines of the file, stripping the terminating \n.
        """
        with self.open(filename, 'r') as f:
            for line in f:
                # Strip final \n
                yield line[:-1]

    def writelines(self, filename, lines, encoding=None):
        """Write a set of lines to a file.

        A \n will be appended to lines before writing.
        """
        with self.open(filename, 'w', encoding=encoding) as f:
            for line in lines:
                f.write(u"%s\n" % line)


class FileSystem(BaseFileSystem):
    """Actual filesystem layer."""
    def open(self, filename, mode, encoding=None):
        encoding = encoding or self.encoding
        full_path = os.path.join(self.root, filename)
        return io.open(full_path, mode, encoding=encoding)


class ReadOnlyFS(BaseFileSystem):
    def open(self, filename, mode, encoding=None):
        for m in mode:
            if m not in ('r', 'b', 't'):
                raise IOError(
                    "Operating on a read-only filesystem, accessing %s with "
                    "invalid mode %s." % (filename, m)) 

        encoding = encoding or self.encoding
        full_path = os.path.join(self.root, filename)
        return io.open(full_path, mode, encoding=encoding)
