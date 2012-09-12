# coding: utf-8
# Copyright (c) 2010-2012 Raphaël Barrois

"""Common action code."""


class BaseAction(object):
    def __init__(self, source, destination, fs, **kwargs):
        super(BaseAction, self).__init__(**kwargs)
        self.source = source
        self.fs = fs

    def forward(self, categories):
        """Apply the action."""
        raise NotImplementedError()

    def backward(self, categories):
        """Revert the action."""
        raise NotImplementedError()


class CopyAction(BaseAction):
    def forward(self, categories):
        self.fs.copy(self.source, self.destination)

    def backward(self, categories):
        self.fs.copy(self.destination, self.source)


class SymLinkAction(BaseAction):
    def forward(self, categories):
        self.fs.create_symlink(
            link_name=self.destination,
            link_target=self.source,
            relative=False,
            force=False)


class FileContentAction(BaseAction):
    """An action based on file *contents*."""

    def forward(self, categories):
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

    def backward(self, categories):
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
    def forward_content(self, source_lines, categories):
        processor = converter.FileProcessor(source_lines, self.fs)
        return processor.forward(categories)

    def backward_content(self, source_lines, categories, modified_lines):
        processor = converter.FileProcessor(source_lines, self.fs)
        return processor.backward(categories, modified_lines)
