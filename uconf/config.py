# -*- coding: utf-8 -*-
# Copyright (c) 2010-2013 Raphaël Barrois
# This software is distributed under the two-clause BSD license.

from __future__ import unicode_literals, absolute_import

"""Handle repository-wide configuration.

These settings only relate to the list of categories, files, ... registered in
the repository, regardless of current settings.
"""


import fnmatch
import os
import stat
import time

import confutils

from . import action_parser
from . import actions
from . import constants
from . import fs
from . import helpers
from . import rule_parser


class FileConfig:
    """Definition of the action for a file."""

    COPY = 'copy'
    SYMLINK = 'symlink'
    PARSE = 'parse'

    ACTIONS = {
        COPY: actions.CopyAction,
        SYMLINK: actions.SymLinkAction,
        PARSE: actions.FileProcessingAction,
    }

    def __init__(self, action, **options):
        if action not in self.ACTIONS:
            raise ValueError("Invalid action %s, choose one of %s" % (
                action, ', '.join(self.ACTIONS)))
        self.action = action
        self.options = options

    def get_destination(self, filename, target=''):
        """Find the appropriate target for a file."""
        if 'dest' in self.options:
            # Explicit target path
            destination = self.options['dest']
        elif 'destdir' in self.options:
            # Replaced destination folder
            destination = os.path.join(self.options['destdir'], os.path.basename(filename))
        else:
            destination = filename

        return helpers.get_absolute_path(destination, base=target)

    def get_action(self, filename, env):
        action = self.ACTIONS[self.action]
        abs_source = helpers.get_absolute_path(filename, base=env.root)
        abs_dest = self.get_destination(filename, env.target)

        return action(source=abs_source, destination=abs_dest, env=env, **self.options)

    def __repr__(self):
        return '<FileConfig: %s %r>' % (self.action, self.options)


class GlobStore:
    def __init__(self, *args):
        self.entries = list(*args)

    def __getitem__(self, key):
        for glob, value in self.entries:
            if fnmatch.fnmatchcase(key, glob):
                return value
        raise KeyError("Key %s not found in %r" % (key, self))

    def __setitem__(self, key, value):
        for i, entry in enumerate(self.entries):
            if key == entry[0]:
                self.entries[i] = (key, value)
        self.entries.append((key, value))

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __repr__(self):
        return "GlobStore(%r)" % self.entries


class RepositoryView:
    """A repository, as seen for a given set of initial categories.

    Attributes:
        base: the Repository on which this view is based
        categories: frozenset of active category names
    """

    def __init__(self, base):
        self.base = base
        self.categories = frozenset()

    def set_initial_categories(self, initial):
        self.categories = frozenset(initial)
        for category_rule, extra_categories in self.base.category_rules:
            if category_rule.test(self.categories):
                self.categories |= extra_categories

    def iter_files(self):
        """Retrieve all active files for this view

        Yields:
            filename
        """
        for file_rule, filename in self.base.file_rules:
            if file_rule.test(self.categories):
                yield filename

    def get_file_config(self, filename, default_action='parse'):
        default_config = FileConfig(default_action)
        return self.base.file_configs.get(filename, default_config)


class Repository:
    """Holds repository configuration.

    Attributes:
        categories (str set): all categories
        files (str list): all managed files
        file_actions (dict(str => FileConfig)): actions for files
        rule_lexer (rule_parser.RuleLexer): lexer to use for rule parsing
    """

    def __init__(self, root=None, *args, **kwargs):
        self.root = root
        self.config = confutils.ConfigFile()
        self.actions_config = self.config.section_view('actions')
        self.files_config = self.config.section_view('files', True)
        self.categories_config = self.config.section_view('categories', True)

        self.category_rules = []
        self.file_rules = []
        self.file_configs = GlobStore()
        self.rule_lexer = rule_parser.RuleLexer()
        self.action_lexer = action_parser.ActionLexer()

        self._read_config()

    @property
    def uconf_dir(self):
        return os.path.join(self.root, constants.REPO_SUBFOLDER)

    @property
    def config_path(self):
        return os.path.join(self.uconf_dir, 'config')

    def extract(self, initial):
        """Extract a 'view' on this repository for given initial categories."""
        view = RepositoryView(self)
        view.set_initial_categories(initial)
        return view

    def write_config(self, fs):
        """Update the configuration."""
        temp_name = '.config-%s.new' % time.strftime('%Y%m%d%H%M%S')
        temp_path = os.path.join(self.uconf_dir, temp_name)

        with fs.open(temp_path, 'wt') as f:
            self.config.write(f)

        fs.rename(temp_path, self.config_path)

    def _read_config(self):
        if not self.root:
            return

        self.config.parse_file(self.config_path, skip_unreadable=False)

        self._read_category_rules(self.categories_config)
        self._read_file_rules(self.files_config)
        self._read_file_actions(self.actions_config)

    def _read_category_rules(self, rules):
        for rule_text, extra_categories in rules.items():
            rule = self.rule_lexer.get_rule(rule_text)
            self.category_rules.append((rule, helpers.flatten(extra_categories)))

    def _read_file_rules(self, rules):
        for rule_text, filenames in rules.items():
            rule = self.rule_lexer.get_rule(rule_text)
            for filename in helpers.flatten(filenames, ' '):
                self.file_rules.append((rule, filename))

    def _read_file_actions(self, actions):
        for filename, action_text in actions.items():
            action_parts = action_text.strip().split(' ', 1)
            action = action_parts.pop(0)
            if action_parts:
                option_text = action_parts[0]
                options = self.action_lexer.get_options(option_text)
            else:
                options = {}

            self.file_configs[filename] = FileConfig(action, **options)


class Env:
    """Holds all configuration for the current environment.

    Attributes:
        repository (Repository): the parsed view of the active repository
        root (str): the path to the repository root
        config (MergedConfig): active configuration directives
    """

    def __init__(self, root, repository, config):
        self.root = root
        self.repository = repository
        self.config = config
        target = self.config.get('target')
        if target:
            target = helpers.get_absolute_path(target, base=self.root)
        self.target = target

        self._forward_fs = self._backward_fs = self._uconf_fs = self._repo_fs = None

    @property
    def uconf_dir(self):
        return os.path.join(self.root, constants.REPO_SUBFOLDER)

    def isset(self, key):
        """Check whether a non-default has been set for a given key."""
        value = self.get(key, default=confutils.NoDefault)
        return value != confutils.NoDefault

    def get(self, key, default=None):
        return self.config.get(key, default)

    def getlist(self, key, default=(), separator=' '):
        value = self.get(key, default=default)
        if isinstance(value, str):
            value = value.split(separator)
        return list(value)

    def get_active_repository(self, initial_cats):
        # TODO(rbarrois): consider memoizing
        return self.repository.extract(initial_cats)

    def get_forward_fs(self):
        if self._forward_fs is None:
            self._forward_fs = fs.FSLoader(
                self.target,
                dry_run=self.get('dry_run', False),
                default_encoding=self.get('file_encoding', 'utf8'),
            )
        return self._forward_fs

    def get_backward_fs(self):
        if self._backward_fs is None:
            self._backward_fs = fs.FSLoader(
                self.root,
                dry_run=self.get('dry_run', False),
                default_encoding=self.get('file_encoding', 'utf8'),
            )
        return self._backward_fs

    def get_uconf_fs(self):
        """Retrieve the filesystem associated with the private uconf dir."""
        if self._uconf_fs is None:
            self._uconf_fs = fs.FSLoader(
                self.uconf_dir,
                dry_run=self.get('dry_run', False),
                default_encoding=self.get('file_encoding', 'utf8'),
            )
        return self._uconf_fs

    def get_repo_fs(self):
        """Retrieve a filesystem for the repository, including uconf."""
        if self._repo_fs is None:
            self._repo_fs = fs.FSLoader(
                self.root,
                dry_run=self.get('dry_run', False),
                default_encoding=self.get('file_encoding', 'utf8'),
            )
        return self._repo_fs

    @classmethod
    def _walk_root(cls, base):
        """Walk to the top of a directory tree until a repository root is found.

        Stops at the first folder containing a '.uconf' subdirectory.
        """
        current = helpers.get_absolute_path(base)
        prev = None
        while prev != current:
            maybe_config = os.path.join(current, constants.REPO_SUBFOLDER)
            if os.access(maybe_config, os.F_OK):
                dirmode = os.stat(maybe_config).st_mode
                if stat.S_ISDIR(dirmode):
                    return current
            prev, current = current, os.path.dirname(current)

    @classmethod
    def _read_config(cls, repo_root=None, config_files=constants.CONFIG_FILES):
        """Read all relevant config files."""
        if repo_root:
            repo_root = cls._walk_root(repo_root)

        config = confutils.ConfigFile()

        for config_file in config_files:
            config_file = helpers.get_absolute_path(config_file)
            config.parse_file(config_file, skip_unreadable=True)

        if repo_root:
            repo_config = os.path.join(repo_root, constants.REPO_SUBFOLDER, 'config')
            config.parse_file(repo_config, skip_unreadable=False)

        return repo_root, config

    @classmethod
    def _merge_config(cls, config, sections=(), extra=None):
        merged = confutils.MergedConfig()
        if extra is not None:
            merged.add_options(extra)

        for section in sections:
            merged.add_options(config.section_view(section))

        merged.add_options(config.section_view('core'))

        return merged

    @classmethod
    def from_files(cls, repo_root=None, config_files=constants.CONFIG_FILES, sections=(), extra=None):
        """Build a Env from basic informations:

        - Path to a repository root
        - List of global configuration files to read
        - List of configuration sections to take into account
        - Dict of extra configuration values
        """

        repo_root, config = cls._read_config(repo_root=repo_root, config_files=config_files)

        repo = Repository(root=repo_root)

        config_view = cls._merge_config(config, sections=sections, extra=extra)

        return cls(root=repo_root, config=config_view, repository=repo)
