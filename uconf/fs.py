# -*- coding: utf-8 -*-
# Copyright (c) 2010-2012 Raphaël Barrois
# This software is distributed under the two-clause BSD license.

from __future__ import unicode_literals, absolute_import

"""Abstract the filesystem layer."""

import codecs
from fs import osfs, multifs, mountfs, memoryfs
from fs.wrapfs import readonlyfs
import hashlib
import io
import logging
import os
import stat

from . import helpers


logger = logging.getLogger(__name__)


class FileSystem(object):
    def __init__(self, *write_paths, **kwargs):
        self.dry_run = kwargs.pop('dry_run', False)
        self.default_encoding = kwargs.pop('default_encoding', None)
        self.write_paths = write_paths
        self.fs, self.subfs = self._prepare_fs(write_paths, dry_run=self.dry_run)

    def _make_merged_fs(self, paths, memory=False):
        """Make a (merged) filesystem for a given set of paths.

        If ``memory`` is True, the resulting filesystem will only use
        memoryfs; otherwise, it will be backed by actual osfs.OSFS.

        Returns:
            (fs, dict(path => fs)): the resulting filesystem, and a dict mapping
                each path to the related filesystem
        """
        if memory:
            fs_class = lambda path: memoryfs.MemoryFS()
        else:
            fs_class = lambda path: osfs.OSFS(path)

        merged_fs = mountfs.MountFS()
        filesystems = {}
        for path in paths:
            fs = fs_class(path)
            merged_fs.mount(path, fs)
            filesystems[path] = fs

        return merged_fs, filesystems

    def _prepare_fs(self, paths, dry_run=False):
        """Prepare the filesystem for a set of writable paths."""
        base_fs = multifs.MultiFS()
        merged_fs, sub_filesystems = self._make_merged_fs(paths)
        if dry_run:
            memory_fs, sub_filesystems = self._make_merged_fs(paths, memory=True)
            base_fs.addfs('memory', memory_fs, write=True)

        base_fs.addfs('targets', merged_fs, write=not dry_run)
        base_fs.addfs('base', readonlyfs.ReadOnlyFS(osfs.OSFS('/')))

        return base_fs, sub_filesystems

    def get_changes(self):
        if self.dry_run:
            for path, fs in self.subfs.items():
                for subpath in fs.walkfiles():
                    length = len(fs.getcontents(subpath))
                    yield '%s%s' % (path, subpath), length

    def __del__(self):
        try:
            if self.dry_run:
                for path, lenth in self.get_changes():
                    logger.info("[Dry-run] Updated path %s (%d bytes)", path, lenth)
        except:
            # Something went wrong while deleting ourselves.
            pass

    def __getattr__(self, name):
        return getattr(self.fs, name)

    def copy(self, source, destination, allow_overwrite=True):
        needs_overwrite = self.exists(destination)
        overwrite = needs_overwrite and allow_overwrite
        return self.fs.copy(source, destination, overwrite=overwrite)

    def open(self, filename, mode='r', encoding=None, **kwargs):
        encoding = encoding or self.default_encoding

        if encoding and 'b' not in mode:
            # Text mode requested, and some encoding was given.
            # We don't trust the underlying layers for unicode handling.
            if 't' in mode:
                mode = mode.replace('t', 'b')
            else:
                mode += 'b'

            writer = codecs.getwriter(encoding)
            reader = codecs.getreader(encoding)

            wrapper = lambda stream: reader(writer(stream))
        else:
            wrapper = lambda stream: stream

        base_file = self.fs.open(filename, mode, **kwargs)
        return wrapper(base_file)

    def read_one_line(self, filename, encoding=None):
        """Read one (stripped) line from a file.

        Typically used to read a password.
        """
        with self.open(filename, 'rt', encoding=encoding) as f:
            return f.readline().strip()

    def readlines(self, filename, encoding=None):
        """Read all lines from a file.

        Yields lines of the file, stripping the terminating \n.
        """
        with self.open(filename, 'rt', encoding=encoding) as f:
            for line in f:
                if line and line[-1] == '\n':
                    # Strip final \n
                    line = line[:-1]
                yield line

    def get_hash(self, filename):
        """Return a simple hash for the file."""
        file_hash = hashlib.md5()
        read_size = 32768
        with self.open(filename, 'rb') as f:
            data = f.read(read_size)
            while data:
                file_hash.update(data)
                data = f.read(read_size)
        return file_hash

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
