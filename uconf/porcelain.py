# -*- coding: utf-8 -*-
# Copyright (c) 2010-2013 Raphaël Barrois
# This software is distributed under the two-clause BSD license.


"""Low level actions for uconf."""


import difflib
import logging
import os.path

from . import helpers


class PorcelainError(Exception):
    def __init__(self, user_message):
        self.user_message = user_message
        super().__init__()


class Porcelain:
    def __init__(self, env, active_repo=None):
        self.env = env
        self.active_repo = active_repo
        self.logger = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))

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
            text = '%s %s' % (text, ' '.join('%s=%s' % param for param in action_params))
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
            for target in targets
        ]

        if storage_folder:
            storage_folder = helpers.get_relative_path(self.env.root, storage_folder, base=self.env.root)

            return [
                (os.path.join(storage_folder, os.path.basename(t)), t)
                for t in targets
            ]

        else:
            return [(t, t) for t in targets]

    def handle(self, files, categories, action=None, action_params=(), folder=None, *args, **kwargs):
        files_config = self.env.repository.files_config
        actions_config = self.env.repository.actions_config

        # Cleanup paths
        paths = self._prepare_files(files, storage_folder=folder)
        files_text = ' '.join(storage for storage, _install in paths)

        # Add to the 'files' section
        if files_text in list(files_config[categories]):
            self.logger.warning("Files '%s' already registered for categories %r", files_text, categories)
        else:
            self.logger.info("Registering files '%s' for categories %r", files_text, categories)
            files_config.add(categories, files_text)

        # Handle dedicated action/options for files
        for storage, install in paths:
            file_params = list(action_params)
            if storage != install:
                file_params.append(('dest', install))

            action_text = self._make_action_text(action, file_params)
            if action_text:
                self.logger.info("Adding rule %r for files '%s'", action_text, storage)
                actions_config[storage] = action_text

        # Write out the configuration
        self.env.repository.write_config(self.env.get_uconf_fs())


class RenameFile(Porcelain):
    """Rename a file within the repository."""

    def _rename_in_files(self, source, dest):
        repo_files = self.env.repository.files_config
        updates = []
        for categories, file_lists in repo_files.items():
            if source in helpers.flatten(file_lists):
                updates.append((categories, file_lists))

        for categories, old_files in updates:
            new_files = [fl.replace(source, dest) for fl in old_files]
            repo_files[categories] = new_files

    def _rename_in_actions(self, source, dest):
        """Rename the file in the 'actions' section of the repo's config."""
        repo_actions = self.env.repository.actions_config
        if source in repo_actions:
            repo_actions[dest] = repo_actions.pop(source)

    def handle(self, source, dest, *args, **kwargs):
        """Renames a file within the repository, both on disk and in config.

        The source and dest arguments should be relative to the repository root.
        """
        source = helpers.get_relative_path(self.env.root, source, base=self.env.root)
        dest = helpers.get_relative_path(self.env.root, dest, base=self.env.root)

        self._rename_in_files(source, dest)
        self._rename_in_actions(source, dest)

        abs_source = helpers.get_absolute_path(source, base=self.env.root)
        abs_dest = helpers.get_absolute_path(dest, base=self.env.root)

        fs = self.env.get_repo_fs()
        fs.rename(abs_source, abs_dest)
        self.env.repository.write_config(fs)


class FilePorcelain(Porcelain):
    """Porcelain command for a single file."""

    def handle(self, filename, *args, **kwargs):
        if self.active_repo is None:
            raise PorcelainError("This porcelain command requires an active repository.")

        try:
            file_config = self.active_repo.get_file_config(
                filename,
                default_action=self.env.get('default_action', 'parse'),
            )
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
        planned, actual = action.diff(self.active_repo.categories)
        if planned != actual:
            diff = difflib.unified_diff(
                actual, planned,
                fromfile=action.destination, tofile=action.destination, lineterm='',
            )
            diff = ('',) + tuple(diff)
            diff = '\n'.join(diff)
            self.logger.info("File %s has changed: %s", filename, diff)


class BackDiffFile(FilePorcelain):
    def handle_file(self, filename, file_config):
        action = file_config.get_action(filename, self.env)
        planned, actual = action.backdiff(self.active_repo.categories)
        if planned != actual:
            diff = difflib.unified_diff(
                actual, planned,
                fromfile=action.source, tofile=action.source, lineterm='',
            )
            diff = ('',) + tuple(diff)
            diff = '\n'.join(diff)
            self.logger.info("File %s has changed: %s", filename, diff)
