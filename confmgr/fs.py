# coding: utf-8
# Copyright (c) 2010-2012 Raphaël Barrois

"""Abstract the filesystem layer."""

import io
import os
import stat

class BaseFileSystem(object):
    """Abstraction layer around the file system.

    All files are expected to be UTF8-encoded.
    """
    def __init__(self, root, encoding='utf8'):
        self.root = root
        self.encoding = encoding

    # Low-level directives
    def _access(self, filename, mode):
        raise NotImplementedError()

    def _open(self, filename, mode):
        raise NotImplementedError()

    def _stat(self, filename):
        raise NotImplementedError()

    def _chmod(self, filename, mode):
        raise NotImplementedError()

    def _chown(self, filename, uid, gid):
        raise NotImplementedError()

    def _symlink(self, link_name, target):
        raise NotImplementedError()

    def _mkdir(self, path):
        """Create a directory, also creating all parents if needed."""
        raise NotImplementedError()

    # Helpers
    def normalize_path(self, path):
        if os.path.isabs(path):
            return path
        return os.path.normpath(os.path.join(self.root, path))

    def split_path(self, path):
        """Convert a (normalized) path to a list of its parent.

        >>> split_path('/foo/bar/baz')
        ['/', '/foo', '/foo/bar', '/foo/bar/baz']
        """
        if path == '/':
            return [path]
        parts = []
        head = tail = path
        while tail:
            parts.append(head)
            head, tail = os.path.split(path)
            path = head
        return reversed(parts)

    # Base commands
    def access(self, path, read=True, write=False):
        """Whether a file can be accessed."""
        mode = os.F_OK
        if read:
            mode |= os.R_OK
        if write:
            mode |= os.W_OK
        return self._access(self.normalize_path(path), mode)

    def file_exists(self, path):
        """Whether the path exists, and is a file."""
        path = self.normalize_path(path)
        if not self._access(path, os.F_OK):
            return False
        f_stat = self._stat(path)
        return stat.S_ISREG(f_stat)

    def dir_exists(self, path):
        path = self.normalize_path(path)
        if not self._access(path, os.F_OK):
            return False
        f_stat = self._stat(path)
        return stat.S_ISDIR(f_stat)

    def mkdir(self, path):
        path = self.normalize_path(path)
        for part in self.split_path(path):
            if self.access(part) and not self.dir_exists(part):
                # Something there, but not a dir
                raise IOError("Parent %s of %s is not a directory" %
                    (part, path))
            elif not self.dir_exists(part):
                self._mkdir(part)

    def open(self, filename, mode, encoding=None):
        return self._open(self.normalize_path(filename), mode, encoding=encoding)

    def stat(self, filename):
        return self._stat(self.normalize_path(filename))

    def chmod(self, filename, mode):
        settable_mode = stat.S_IMODE(mode)
        return self._chmod(self.normalize_path(filename), settable_mode)

    def chown(self, filename, uid, gid):
        return self._chown(self.normalize_path(filename), uid, gid)

    def symlink(self, link_name, target):
        return self._symlink(
            self.normalize_path(link_name),
            self.normalize_path(target),
        )

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

    def copy(self, source, destination, copy_mode=True, copy_user=False):
        with self.open(source, 'rb') as src:
            with self.open(destination, 'wb') as dst:
                dst.write(src.read())

        if copy_mode or copy_user:
            stat = self._stat(source)
            if copy_mode:
                self.chmod(destination, stat.st_mode)
            if copy_user:
                self.chown(destination, stat.st_uid, stat.st_gid)

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
    def _access(self, filename, mode):
        return os.access(filename, mode)

    def _open(self, filename, mode, encoding=None):
        encoding = encoding or self.encoding
        return io.open(filename, mode, encoding=encoding)

    def _stat(self, filename):
        return os.stat(filename)

    def _chmod(self, filename, mode):
        return os.chmod(filename, mode)

    def _chown(self, filename, uid, gid):
        return os.chown(filename, uid, gid)

    def _symlink(self, link_name, target):
        return os.symlink(target, link_name)

    def _mkdir(self, path):
        os.mkdir(path)


class ReadOnlyFS(BaseFileSystem):

    def _ro_forbidden(self, msg, *args):
        raise IOError("Read-Only filesystem: " + msg % args)

    def _access(self, filename, mode):
        return os.access(filename, mode)

    def _open(self, filename, mode, encoding=None):
        for m in mode:
            if m not in ('r', 'b', 't'):
                self._ro_forbidden("Accessing %s with invalid mode %s.",
                    filename, m)

        encoding = encoding or self.encoding
        return io.open(filename, mode, encoding=encoding)

    def _stat(self, filename):
        return os.stat(filename)

    def _chmod(self, filename, mode):
        self._ro_forbidden("Cannot change mode of %s.", filename)

    def _chown(self, filename, uid, gid):
        self._ro_forbidden("Cannot change uid/gid of %s to %s:%s",
            filename, uid, gid)

    def _symlink(self, link_name, target):
        self._ro_forbidden("Cannot symlink %s to %s", link_name, target)

    def _mkdir(self, path):
        self._ro_forbidden("Cannot create folder %s", path)
