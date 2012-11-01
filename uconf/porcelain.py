# coding: utf-8
# Copyright (c) 2010-2012 Raphaël Barrois


from __future__ import absolute_import, unicode_literals


"""Low level actions for uconf."""


import difflib
import logging
import os.path

from . import helpers

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


class ImportFiles(Porcelain):
    def _make_action_text(self, action=None, action_params=()):
        if action:
            text = action
        elif action_params:  # Default action, but overridden params
            text = 'parse'
        else:
            return ''

        if action_params:
            text = '%s %s' % (text,
                ' '.join('%s=%s' % param for param in action_params))
        return text

    def _prepare_files(self, targets, storage_folder=None):
        """Converts a set of files to a list of (storage, target) pairs.

        The returned (storage, target) pairs are relative paths:
            - the 'storage' path is relative to the repository root
            - the 'target' path is relative to the install root
        """
        target_root = self.env.target

        targets = [
            helpers.get_relative_path(target_root, target, base=target_root)
            for target in targets]

        if storage_folder:
            storage_folder = helpers.get_relative_path(
                self.env.root, storage_folder, base=self.env.root)

            return [
                (os.path.join(storage_folder, os.path.basename(t)), t)
                for t in targets]

        else:
            return [(t, t) for t in targets]

    def handle(self, files, categories, action=None, action_params=(),
            folder=None, *args, **kwargs):
        repo_config = self.env.repository.config

        # Cleanup paths
        paths = self._prepare_files(files, storage_folder=folder)
        files_text = ' '.join(storage for storage, _install in paths)

        # Add to the 'files' section
        if files_text in list(repo_config.get('files', categories)):
            self.logger.warning("Files '%s' already registered for categories %r",
                files_text, categories)
        else:
            self.logger.info("Registering files '%s' for categories %r",
                files_text, categories)
            repo_config.add('files', categories, files_text)

        # Handle dedicated action/options for files
        for storage, install in paths:
            file_params = list(action_params)
            if storage != install:
                file_params.append(('dest', install))

            action_text = self._make_action_text(action, file_params)
            if action_text:
                self.logger.info("Adding rule %r for files '%s'",
                    action_text, storage)
                repo_config.add_or_update('actions', storage, action_text)

        # Write out the configuration
        self.env.repository.write_config(self.env.get_repo_fs())


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


class BackDiffFile(FilePorcelain):
    def handle_file(self, filename, file_config):
        action = file_config.get_action(filename, self.env)
        old, new = action.backdiff(self.active_repo.categories)
        if old != new:
            diff = difflib.unified_diff(old, new,
                fromfile=action.source, tofile=action.source, lineterm='')
            diff = ('',) + tuple(diff)
            diff = '\n'.join(diff)
            self.logger.info("File %s has changed: %s", filename, diff)
