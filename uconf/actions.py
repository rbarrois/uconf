# -*- coding: utf-8 -*-
# Copyright (c) 2010-2013 Raphaël Barrois
# This software is distributed under the two-clause BSD license.

from __future__ import absolute_import, unicode_literals

"""Common action code."""

import functools
import os.path

from . import converter
from . import fs


def catch_fs_exceptions(fun):
    @functools.wraps(fun)
    def decorated(self, *args, **kwargs):
        try:
            return fun(self, *args, **kwargs)
        except fs.FSError as e:
            print("Error while performing %s.%s(%s -> %s): %s" % (
                self.__class__.__name__, fun.__name__,
                self.source, self.destination,
                e))
            raise
    return decorated


class BaseAction:
    def __init__(self, source, destination, env, **kwargs):
        self.source = source
        self.destination = destination
        self.env = env
        self.fs = None

    @catch_fs_exceptions
    def forward(self, categories):
        """Apply the action."""
        self.fs = self.env.get_forward_fs()
        self._ensure_dir_exists(self.destination)
        self._forward(categories)

    def _forward(self, categories):
        raise NotImplementedError()

    @catch_fs_exceptions
    def backward(self, categories):
        """Revert the action."""
        self.fs = self.env.get_backward_fs()
        self._ensure_dir_exists(self.source)
        self._backward(categories)

    def _backward(self, categories):
        raise NotImplementedError()

    @catch_fs_exceptions
    def diff(self, categories):
        """Compute the differences between planned and actual file content."""
        self.fs = self.env.get_forward_fs()
        return self._diff(categories)

    def _diff(self, categories):
        raise NotImplementedError()

    @catch_fs_exceptions
    def backdiff(self, categories):
        """Compute the differences between original and backported file content."""
        self.fs = self.env.get_backward_fs()
        return self._backdiff(categories)

    def _backdiff(self, categories):
        raise NotImplementedError()

    def _ensure_dir_exists(self, path):
        dirname = os.path.dirname(path)
        self.fs.makedirs(dirname)

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.source)


class CopyAction(BaseAction):
    def _copy_or_symlink(self, source, destination):
        if self.fs.symlink_exists(source):
            target = self.fs.readlink(source)
            self.fs.symlink(destination, target)
        else:
            self.fs.copy(source, destination)

    def _forward(self, categories):
        self._copy_or_symlink(self.source, self.destination)

    def _backward(self, categories):
        self._copy_or_symlink(self.destination, self.source)

    def _diff(self, categories):
        source_hash = self.fs.get_hash(self.source).hexdigest()
        if self.fs.file_exists(self.destination):
            dest_hash = self.fs.get_hash(self.destination).hexdigest()
        else:
            dest_hash = '!' * len(source_hash)
        return [source_hash], [dest_hash]

    def _backdiff(self, categories):
        source, dest = self._diff(categories)
        # Simply reverse the diff
        return dest, source


class SymLinkAction(BaseAction):
    def _forward(self, categories):
        self.fs.create_symlink(
            link_name=self.destination,
            target=self.source,
            relative=False,
            force=False,
        )

    def _backward(self, categories):
        pass

    def _diff(self, categories):
        if self.fs.symlink_exists(self.destination):
            target = 'link: ' + self.fs.readlink(self.destination)
        elif self.fs.file_exists(self.destination):
            target = 'reg: ' + self.fs.get_hash(self.destination).hexdigest()
        else:
            target = '<none>'
        return ['link: ' + self.source], [target]

    def _backdiff(self, categories):
        source, dest = self._diff(categories)
        return dest, source


class FileContentAction(BaseAction):
    """An action based on file *contents*."""

    def _forward(self, categories):
        source_lines = self._readlines(self.source)
        destination_lines = self.forward_content(source_lines, categories)

        self.fs.writelines(self.destination, destination_lines)

    def forward_content(self, source_lines, categories):
        """Convert the source file, based on its lines.

        Args:
            source_lines (str list): lines of the original file
            categories (str list): active categories

        Yields:
            str: lines of the destination file
        """
        raise NotImplementedError()

    def _backward(self, categories):
        source_lines = self._readlines(self.source)
        modified_lines = self._readlines(self.destination)
        updated_lines = self.backward_content(source_lines, categories, modified_lines)

        self.fs.writelines(self.source, updated_lines)

    def backward_content(self, source_lines, categories, modified_lines):
        """Convert back the modified file, based on its lines.

        Args:
            source_lines (str list): lines of the original file
            categories (str list): active categories
            modified_lines (str list): lines of the modified files

        Yields:
            str: new lines for the source file
        """
        raise NotImplementedError()

    def _readlines(self, path, ignore_empty=True):
        if ignore_empty and not self.fs.file_exists(path):
            return []
        return self.fs.readlines(path)

    def _diff(self, categories):
        source_lines = self._readlines(self.source)
        planned_lines = self.forward_content(source_lines, categories)
        actual_lines = self._readlines(self.destination)

        return list(planned_lines), list(actual_lines)

    def _backdiff(self, categories):
        source_lines = list(self._readlines(self.source))
        destination_lines = list(self._readlines(self.destination))
        backported_lines = self.backward_content(
                source_lines, categories, destination_lines)

        return list(backported_lines), source_lines


class FileProcessingAction(FileContentAction):
    """Process a file, using usual rules."""
    def forward_content(self, source_lines, categories):
        processor = converter.FileProcessor(source_lines, self.fs)
        return processor.forward(categories)

    def backward_content(self, source_lines, categories, modified_lines):
        processor = converter.FileProcessor(source_lines, self.fs)
        return processor.backward(categories, modified_lines)
