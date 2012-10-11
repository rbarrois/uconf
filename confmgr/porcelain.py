# coding: utf-8
# Copyright (c) 2010-2012 Raphaël Barrois


from __future__ import absolute_import, unicode_literals


"""Low level actions for confmgr."""


import difflib
import logging


class PorcelainError(Exception):
    def __init__(self, user_message):
        self.user_message = user_message
        super(PorcelainError, self).__init__()


class Porcelain(object):
    def __init__(self, env, active_repo=None):
        self.env = env
        self.active_repo = active_repo
        self.logger = logging.getLogger(
            '%s.%s' % (__name__, self.__class__.__name__))

    def handle(self, *args, **kwargs):
        """Run the porcelain command.

        Raises:
            PorcelainError: if anything went wrong.
        """
        raise NotImplementedError()


class FilePorcelain(Porcelain):
    """Porcelain command for a single file."""

    def handle(self, filename, *args, **kwargs):
        if self.active_repo is None:
            raise PorcelainError("This porcelain command requires an active repository.")

        try:
            file_config = self.active_repo.get_file_config(filename,
                    default_action=self.env.get('default_action', 'parse'))
        except KeyError:
            raise PorcelainError("File %s not in repository." % filename)

        self.handle_file(filename, file_config, *args, **kwargs)


class MakeFile(FilePorcelain):
    def handle_file(self, filename, file_config):
        action = file_config.get_action(filename, self.env)
        self.logger.info("Building file %s (%s)", filename, action.__class__.__name__)
        action.forward(self.active_repo.categories)


class BackFile(FilePorcelain):
    def handle_file(self, filename, file_config):
        action = file_config.get_action(filename, self.env)
        self.logger.info("Backporting file %s (%s)", filename, action.__class__.__name__)
        action.backward(self.active_repo.categories)


class DiffFile(FilePorcelain):
    def handle_file(self, filename, file_config):
        action = file_config.get_action(filename, self.env)
        old, new = action.diff(self.active_repo.categories)
        if old != new:
            diff = difflib.unified_diff(old, new,
                fromfile=action.destination, tofile=action.destination, lineterm='')
            diff = ('',) + tuple(diff)
            diff = '\n'.join(diff)
            self.logger.info("File %s has changed: %s", filename, diff)
