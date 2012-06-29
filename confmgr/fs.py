# coding: utf-8
# Copyright (c) 2010-2012 Raphaël Barrois

"""Abstract the filesystem layer."""

import os

class BaseFileSystem(object):
    def __init__(self, root):
        self.root = root

    def open(self, filename, mode):
        raise NotImplementedError()

    def read_one_line(self, filename):
        with self.open(filename, 'r') as f:
            return f.readline().strip()

    def readlines(self, filename):
        with self.open(filename, 'r') as f:
            for line in f:
                # Strip final \n
                return line[:-1]

    def writelines(self, filename, lines, encoding='utf8'):
        with self.open(filename, 'w') as f:
            for line in lines:
                f.write('%s\n' % line.encode(encoding))


class FileSystem(BaseFileSystem):
    def open(self, filename, mode):
        full_path = os.path.join(self.root, filename)
        return open(full_path, mode)
