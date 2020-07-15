# -*- coding: utf-8 -*-
# Copyright (c) 2010-2013 Raphaël Barrois
# This software is distributed under the two-clause BSD license.

"""Abstract the filesystem layer."""

import logging

import fslib
import fslib.builders
import fslib.stacking


logger = logging.getLogger(__name__)


FSError = fslib.FSError


class FSLoader:
    def __init__(self, *write_paths, **kwargs):
        self.dry_run = kwargs.pop('dry_run', False)
        self.default_encoding = kwargs.pop('default_encoding', 'utf-8')
        self.write_paths = write_paths
        self.fs, self.subfs = self._prepare_fs(write_paths, dry_run=self.dry_run)

    def _prepare_fs(self, paths, dry_run=False):
        """Prepare the filesystem for a set of writable paths."""
        base_fs = fslib.stacking.MountFS()
        base = fslib.stacking.ReadOnlyFS(fslib.OSFS())
        base_fs.mount_fs(base, fslib.ROOT)

        sub_filesystems = {}

        for path in paths:
            subfs = fslib.OSFS(mapped_root=path)
            if dry_run:
                ro_fs = fslib.stacking.ReadOnlyFS(subfs)
                mem_fs = fslib.builders.make_memory_fake()
                union_fs = fslib.stacking.UnionFS()
                union_fs.add_branch(mem_fs, 'mem', rank=0, writable=True)
                union_fs.add_branch(ro_fs, 'os_ro', rank=1, writable=False)
                subfs = union_fs
                sub_filesystems[path] = mem_fs
            base_fs.mount_fs(subfs, path)

        return fslib.FileSystem(base_fs), sub_filesystems

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
        except Exception as e:
            # Something went wrong while deleting ourselves.
            logger.exception("Failure while deleting %r: %r", self, e)

    def __getattr__(self, name):
        return getattr(self.fs, name)
