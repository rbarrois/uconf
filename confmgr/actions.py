# coding: utf-8
# Copyright (c) 2010-2012 Raphaël Barrois

"""Common action code."""

import os.path

from . import converter


class BaseAction(object):
    def __init__(self, source, destination, fs_config, **kwargs):
        super(BaseAction, self).__init__(**kwargs)
        self.source = source
        self.destination = destination
        self.fs_config = fs_config
        self.fs = None

    def forward(self, categories):
        """Apply the action."""
        self.fs = self.fs_config.get_forward_fs()
        self._ensure_dir_exists(self.destination)
        self._forward(categories)

    def _forward(self, categories):
        raise NotImplementedError()

    def backward(self, categories):
        """Revert the action."""
        self.fs = self.fs_config.get_backward_fs()
        self._ensure_dir_exists(self.source)
        self._backward(categories)

    def _backward(self, categories):
        raise NotImplementedError()

    def _ensure_dir_exists(self, path):
        dirname = os.path.dirname(path)
        self.fs.makedir(dirname, recursive=True, allow_recreate=True)

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.source)


class CopyAction(BaseAction):
    def _forward(self, categories):
        self.fs.copy(self.source, self.destination, overwrite=True)

    def _backward(self, categories):
        self.fs.copy(self.destination, self.source, overwrite=True)


class SymLinkAction(BaseAction):
    def _forward(self, categories):
        self.fs.create_symlink(
            link_name=self.destination,
            link_target=self.source,
            relative=False,
            force=False)


class FileContentAction(BaseAction):
    """An action based on file *contents*."""

    def _forward(self, categories):
        source_lines = self.fs.readlines(self.source)
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
        source_lines = self.fs.readlines(self.source)
        modified_lines = self.fs.readlines(self.destination)
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


class FileProcessingAction(FileContentAction):
    """Process a file, using usual rules."""
    def forward_content(self, source_lines, categories):
        processor = converter.FileProcessor(source_lines, self.fs)
        return processor.forward(categories)

    def backward_content(self, source_lines, categories, modified_lines):
        processor = converter.FileProcessor(source_lines, self.fs)
        return processor.backward(categories, modified_lines)
