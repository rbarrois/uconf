# -*- coding: utf-8 -*-
# Copyright (c) 2010-2012 Raphaël Barrois
# This software is distributed under the two-clause BSD license.

"""Abstract the filesystem layer."""

import io
import os
import stat


class WithPermsFS(object):

                                            # Posix
    PERM_DIR_EDIT = 'dir_edit'              # +w
    PERM_DIR_KEEPOWNER = 'dir_sgid'         # g+s
    PERM_DIR_LIST = 'dir_list'              # +r
    PERM_DIR_STAT = 'dir_stat'              # +x
    PERM_DIR_OWNER_DEL = 'dir_sticky'       # o+t
    PERM_FILE_DELETE = 'file_delete'        # N/A
    PERM_FILE_READ = 'file_read'            # +r
    PERM_FILE_RUN = 'file_run'              # +x
    PERM_FILE_RUNSGID = 'file_sgid'         # g+s
    PERM_FILE_RUNSUID = 'file_suid'         # u+s
    PERM_FILE_OWNER_DEL = 'file_sticky'     # o+t
    PERM_FILE_WRITE = 'file_write'          # u+x

    def supported_perms(self):
        return ()

    def supports_perm(self, perm):
        return perm in self.supported_perms()

    def get_owner(self, path):
        """Retrieve the owner of a path.

        :param path: path to get owner of
        :type path: str

        :returns: UID or name of the owner
        :rtype: str

        :raises UnsupportedError: for FSes not supporting this operation
        :raises PermissionDeniedError: if fetching the owner is not allowed
        """
        raise UnsupportedError("getting path owner")

    def set_owner(self, path, owner):
        """Set the owning user for a path.

        :param path: path to change owner of
        :type path: str
        :param owner: name or UID of the new owner of the path
        :type owner: str

        :raises UnsupportedError: for FSes not supporting this operation
        :raises PermissionDeniedError: if changing the owner is not allowed
        """
        raise UnsupportedError('set owner', path=path)

    def get_group(self, path):
        """Retrieve the owning group of a path.

        :param path: path to get owning group of
        :type path: str

        :returns: GID or name of the owning group
        :rtype: str

        :raises UnsupportedError: for FSes not supporting this operation
        :raises PermissionDeniedError: if fetching the owning group is not allowed
        """
        raise UnsupportedError("getting path owning group")

    def set_group(self, path, group):
        """Set the owning group for a path.

        :param path: path to change owning group of
        :type path: str
        :param group: name or GID of the new owning group of the path
        :type group: str

        :raises UnsupportedError: for FSes not supporting this operation
        :raises PermissionDeniedError: if changing the owning group is forbidden
        """
        raise UnsupportedError('set owning group', path=path)

    def chown(self, path, owner, group):
        """Change both owner and owning group in a single call.

        Relies on :meth:`set_owner` and :meth:`set_group`.

        :param path: path to change ownership of
        :type path: str
        :param owner: name or UID of the new owner of the path
        :type owner: str
        :param group: name or GID of the new owning group of the path
        :type group: str

        :raises UnsupportedError: for FSes not supporting this operation
        :raises PermissionDeniedError: if changing path ownership is not allowed
        """
        self.set_owner(path, owner)
        self.set_group(path, group)

    def get_owner_perms(self, path):
        """Fetch current owner permissions for a path.

        :param path: path to get perms of
        :type path: str

        :returns: perms for the path
        :rtype: list of PERM_* entries

        :raises UnsupportedError: for FSes not supporting this operation
        :raises PermissionDeniedError: if getting the owner' perms is forbidden
        """
        raise UnsupportedError("getting owner permissions")

    def set_owner_perms(self, path, *perms):
        """Set new perms for the owning user.

        Relies on :meth:`_apply_owner_perms`.

        :param path: path to set perms to
        :type path: str
        :param perms: perms to set on the path
        :type perms: list of PERM_* entries

        :raises UnsupportedError: for FSes not supporting this operation
        :raises UnsupportedPermError: when trying to set unsupported perms
        :raises PermissionDeniedError: if changing the owner' perms is forbidden
        """
        for perm in perms:
            if not self.supports_perm(perm):
                raise UnsupportedPermError(perm)
        self._apply_owner_perms(path, perms)

    def _apply_owner_perms(self, path, perms):
        raise UnsupportedError("setting owner perms")

    def get_group_perms(self, path):
        """Fetch current group permissions for a path.

        :param path: path to get perms for
        :type path: str

        :returns: perms for the path
        :rtype: list of PERM_* entries

        :raises UnsupportedError: for FSes not supporting this operation
        :raises PermissionDeniedError: if getting the group' perms is forbidden
        """
        raise UnsupportedError("getting group permissions")

    def set_group_perms(self, path, *perms):
        """Set new perms for the owning group.

        Relies on :meth:`_apply_group_perms`.

        :param path: path to set perms to
        :type path: str
        :param perms: perms to set on the path
        :type perms: list of PERM_* entries

        :raises UnsupportedError: for FSes not supporting this operation
        :raises UnsupportedPermError: when trying to set unsupported perms
        :raises PermissionDeniedError: if changing the group' perms is forbidden
        """
        for perm in perms:
            if not self.supports_perm(perm):
                raise UnsupportedPermError(perm)
        self._apply_group_perms(path, perms)

    def _apply_group_perms(self, path, perms)
        raise UnsupportedError("setting group perms")

    def get_world_perms(self, path):
        """Fetch current world permissions for a path.

        :param path: path to get perms for
        :type path: str

        :returns: perms for the path
        :rtype: list of PERM_* entries

        :raises UnsupportedError: for FSes not supporting this operation
        :raises PermissionDeniedError: if getting the world' perms is forbidden
        """
        raise UnsupportedError("getting world permissions")

    def set_world_perms(self, path, *perms):
        """Set new perms for 'other' users.

        Relies on :meth:`_apply_world_perms`.

        :param path: path to set perms to
        :type path: str
        :param perms: perms to set on the path
        :type perms: list of PERM_* entries

        :raises UnsupportedError: for FSes not supporting this operation
        :raises UnsupportedPermError: when trying to set unsupported perms
        :raises PermissionDeniedError: if changing the world' perms is forbidden
        """
        for perm in perms:
            if not self.supports_perm(perm):
                raise UnsupportedPermError(perm)
        self._apply_world_perms(path, perms)

    def _apply_world_perms(self, path, perms):
        raise UnsupportedError("setting world perms")

    def _mode_to_perms(self, mode, for_file, block='owner'):
        """Converts a posix-style mode block to PERM_* combinations."""
        perms = set()
        if mode[0] == 'r':
            perms.add(self.PERM_FILE_READ if for_file else self.PERM_DIR_LIST)
        if mode[1] == 'w':
            perms.add(self.PERM_FILE_WRITE if for_file else self.PERM_DIR_EDIT)
        if mode[2] in ('x', 's', 't'):
            perms.add(self.PERM_FILE_RUN if for_file else self.PERM_DIR_STAT)
        if mode[2] in ('s', 'S'):
            if block == 'owner' and for_file:
                    perms.add(self.PERM_FILE_RUNSUID)
            elif block == 'group':
                perms.add(self.PERM_FILE_RUNSGID if for_file else self.PERM_DIR_KEEPOWNER)
            elif block == 'world':
                perms.add(self.PERM_FILE_STICKY if for_file else self.PERM_DIR_STICKY)
        return perms

    _mode_re = r'^([r-][w-][xsS-]){1,2}([r-][w-][xtT-])?$'

    def chmod_file(self, path, mode):
        """Change the mode of a file.

        :param path: path of the file to change mode
        :type path: str
        :param mode: POSIX-style permission line ('r--rwsr-x'); might be
            truncated to user-only ('r-x') or user+group-only level ('rwsr--').
        :type mode: str

        :raises ValueError: if the mode doesn't respect the expected values.
        :raises UnsupportedError: if the filesystem doesn't support setting perms
        :raises UnsupportedPermError: if some requested perm isn't supported by
            the filesystem
        """
        if not self.isfile(path):
            raise UnsupportedError("using chmod_file on a non-file", path)
        self._chmod(path, mode, for_file=True)

    def chmod_dir(self, path, mode):
        """Change the mode of a directory.

        :param path: path of the directory to change mode
        :type path: str
        :param mode: POSIX-style permission line ('r--rwsr-x'); might be
            truncated to user-only or user+group-only level.
        :type mode: str

        :raises ValueError: if the mode doesn't respect the expected values.
        :raises UnsupportedError: if the filesystem doesn't support setting perms
        :raises UnsupportedPermError: if some requested perm isn't supported by
            the filesystem
        """
        if not self.isdir(path):
            raise UnsupportedError("using chmod_dir on a non-dir", path)
        self._chmod(path, mode, for_file=False)

    def _chmod(self, path, mode, for_file)
        """Change the mode of a file/directory.

        :param path: path of the file/directory to change mode of
        :type path: str
        :param mode: POSIX-style permission line ('r--rwsr-x'); might be
            truncated to user-only ('r-x') or user+group-only level ('rwsr--').
        :type mode: str
        :param for_file: whether we are changing the perms of a file or a folder
        :type for_file: bool

        :raises ValueError: if the mode doesn't respect the expected values.
        :raises UnsupportedError: if the filesystem doesn't support setting perms
        :raises UnsupportedPermError: if some requested perm isn't supported by
            the filesystem
        """
        if not re.match(_mode_re, mode):
            raise ValueError("Invalid mode %s, use *nix-style r--rwsr-x" % mode)
        owner = mode[:3]
        self.set_owner_perms(self._mode_to_perms(owner, for_file, 'owner'))
        if len(mode) >= 6:
            group = mode[3:6]
            self.set_group_perms(self._mode_to_perms(group, for_file, 'group'))
        if len(mode) == 9:
            world = mode[6:]
            self.set_world_perms(self._mode_to_perms(world, for_file, 'world'))

    def get_extra_user_perms(self, user, path):
        """Fetch extra user permissions (ACLs) for a path.

        This will *not* perform uid/gid expansion to check for user access, but
        simply return ACLs for the given user.

        :param path: path to get perms of
        :type path: str
        :param user: user name or UID to fetch perms
        :type user: str

        :returns: perms for the path
        :rtype: list of PERM_* entries

        :raises UnsupportedError: for FSes not supporting this operation
        :raises PermissionDeniedError: if getting non-owner perms is forbidden
        """
        raise UnsupportedError("getting non-owner permissions")

    def add_extra_user_perms(self, path, user, *perms):
        """Add extra permissions for a given user.

        :param path: path of the file/directory to add permissions to
        :type path: str
        :param user: name or ID of the user to set permissions to
        :type user: str
        :param perms: permissions to set
        :type perms: list of PERM_* entries
        """
        raise UnsupportedError('add user-level ACLs')

    def get_extra_group_perms(self, group, path):
        """Fetch extra group permissions (ACLs) for a path.

        This will *not* perform uid/gid expansion to check for group access, but
        simply return ACLs for the given group.

        :param path: path to get perms of
        :type path: str
        :param group: group name or GID to fetchgroups
        :type group: str

        :returns: perms for the path
        :rtype: list of PERM_* entries

        :raises UnsupportedError: for FSes not supporting this operation
        :raises PermissionDeniedError: if getting non-group perms is forbidden
        """
        raise UnsupportedError("getting non-owning group permissions")

    def add_extra_group_perms(self, path, group, *perms):
        """Add extra permissions for a given group.

        :param path: path of the file/directory to add permissions to
        :type path: str
        :param group: name or ID of the group to set permissions to
        :type group: str
        :param perms: permissions to set
        :type perms: list of PERM_* entries
        """
        raise UnsupportedError('add group-level ACLs')









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


class FakeFile(object):
    def __init__(self, path, mode, uid, gid):
        self.path = path
        self.mode = mode
        self.uid = uid
        self.gid = gid
        self.content = StringIO.StringIO()

    def open(self, mode, encoding):
        if any(m not in 'rbt' for m in mode) and not (self.mode & stat.S_IWUSR):
            raise IOError("Cannot access %s for writing" % self.path)
        return self.content


class PretendFS(BaseFileSystem):
    def __init__(self, *args, **kwargs):
        super(PretendFS, self).__init__(*args, **kwargs)
        self.fake_symlinks = {}
        self.fake_dirs = []
        self.fake_files = {}

    def _access(self, filename, mode):
        if os.access(filename, mode):
            return True
        elif filename in self.fake_symlinks:
            return self._access(self.fake_symlinks[filename], mode)
        elif filename in self.fake_dirs:
            return True
        elif filename in self.fake_files:
            f_mode, f_uid, g_gid = self.fake_files[filename]
            return mode & f_mode
