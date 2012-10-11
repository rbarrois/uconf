# coding: utf-8
# Copyright (c) 2010-2012 Raphaël Barrois


from __future__ import absolute_import, unicode_literals


"""Low level actions for confmgr."""


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
        try:
            file_config = self.active_repo.get_file_config(filename,
                    default_action=self.env.get('default_action', 'parse'))
        except KeyError:
            raise PorcelainError("File %s not in repository." % filename)

        self.handle_file(filename, file_config, *args, **kwargs)


class MakeFile(FilePorcelain):
    def handle_file(self, filename, file_config):
        action = file_config.get_action(filename, self.env)
        action.forward(self.active_repo.categories)


def BackFile(FilePorcelain):
    def handle_file(self, filename, file_config):
        action = file_config.get_action(filename, self.env)
        action.backward(self.active_repo.categories)
