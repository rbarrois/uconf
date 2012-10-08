# -*- coding: utf-8 -*-

from __future__ import unicode_literals, absolute_import

"""Handle repository-wide configuration.

These settings only relate to the list of categories, files, ... registered in
the repository, regardless of current settings.
"""


import fnmatch
import os
import socket
import stat

from . import action_parser
from . import actions
from . import confhelpers
from . import constants
from . import helpers
from . import rule_parser


class FileConfig(object):
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

    def get_action(self, filename, source, destination, fs_config):
        action = self.ACTIONS[self.action]
        abs_source = helpers.get_absolute_path(filename, base=source)
        abs_dest = helpers.get_absolute_path(filename, base=destination)
        return action(source=abs_source, destination=abs_dest,
            fs_config=fs_config, **self.options)

    def __repr__(self):
        return '<FileConfig: %s %r>' % (self.action, self.options)


class GlobbingDict(dict):
    def __getitem__(self, key):
        for glob, value in self.items():
            if fnmatch.fnmatchcase(key, glob):
                return value
        raise KeyError("Key %s not found in %r" % (key, self))

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __repr__(self):
        return "GlobbingDict(%s)" % super(GlobbingDict, self).__repr__()


class RepositoryView(object):
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
                self.categories |= frozenset(extra_categories)

    def iter_files(self, default_action='parse'):
        """Retrieve all active files for this view, including actions.

        Yields:
            filename, FileConfig
        """
        default_config = FileConfig(default_action)
        for file_rule, filename in self.base.file_rules:
            if file_rule.test(self.categories):
                file_config = self.base.file_configs.get(filename, default_config)
                yield filename, file_config

    def get_action(self, filename, default_action='parse'):
        default_config = FileConfig(default_action)
        return self.base.file_configs.get(filename, default_config)


class Repository(object):
    """Holds repository configuration.

    Attributes:
        categories (str set): all categories
        files (str list): all managed files
        file_actions (dict(str => FileConfig)): actions for files
        rule_lexer (rule_parser.RuleLexer): lexer to use for rule parsing
    """

    def __init__(self, *args, **kwargs):
        self.category_rules = []
        self.file_rules = []
        self.file_configs = GlobbingDict()
        self.rule_lexer = rule_parser.RuleLexer()
        self.action_lexer = action_parser.ActionLexer()

    def extract(self, initial):
        """Extract a 'view' on this repository for given initial categories."""
        view = RepositoryView(self)
        view.set_initial_categories(initial)
        return view

    def _merge_category_rules(self, rules):
        for rule_text, extra_categories in rules.items():
            rule = self.rule_lexer.get_rule(rule_text)
            self.category_rules.append((rule, extra_categories.split()))

    def _merge_file_rules(self, rules):
        for rule_text, filenames in rules.items():
            rule = self.rule_lexer.get_rule(rule_text)
            for filename in filenames.split(' '):
                self.file_rules.append((rule, filename))

    def _merge_file_actions(self, actions):
        for filename, action_text in actions.items():
            action_parts = action_text.strip().split(' ', 1)
            action = action_parts.pop(0)
            if action_parts:
                option_text = action_parts[0]
                options = self.action_lexer.get_options(option_text)
            else:
                options = {}

            self.file_configs[filename] = FileConfig(action, **options)

    def fill_from_config(self, config):
        self._merge_category_rules(config['categories'])
        self._merge_file_rules(config['files'])
        self._merge_file_actions(config['actions'])


class Env(object):
    """Holds all configuration for the current environment.

    Attributes:
        repository (Repository): the parsed view of the active repository
        active_repository (RepositoryView): the active repository view
        prefs (MergedConfig): active configuration directives
    """

    def __init__(self, root, repository, config):
        self.root = root
        self.repository = repository
        self.config = config

    def isset(self, key):
        """Check whether a non-default has been set for a given key."""
        value = self.get(key, default=confhelpers.NoDefault)
        return value != confhelpers.NoDefault

    def get(self, key, default=None):
        return self.config.get(key, default)

    def getlist(self, key, default=(), separator=' '):
        return self.config.get_tuple(key, default=default, separator=separator)

    def get_active_repository(self, initial_cats):
        # TODO(rbarrois): consider memoizing
        return self.repository.extract(initial_cats)

    @classmethod
    def _walk_root(cls, base):
        """Walk to the top of a directory tree until a repository root is found.

        Stops at the first folder containing a '.confmgr' subdirectory.
        """
        prev = None
        base = helpers.get_absolute_path(base)
        while prev != base:
            maybe_config = os.path.join(base, constants.REPO_SUBFOLDER)
            if os.access(maybe_config, os.F_OK):
                dirmode = os.stat(maybe_config).st_mode
                if stat.S_ISDIR(dirmode):
                    return base
            prev, base = base, os.path.dirname(base)

    @classmethod
    def _read_config(cls, repo_root=None, config_files=constants.CONFIG_FILES):
        """Read all relevant config files."""
        if repo_root:
            repo_root = cls._walk_root(repo_root)

        config = confhelpers.ConfigReader(
            multi_valued_sections=('files', 'categories', 'actions'))

        for config_file in config_files:
            config_file = helpers.get_absolute_path(config_file)
            config.parse_file(config_file, skip_unreadable=True)

        if repo_root:
            repo_config = os.path.join(repo_root,
                constants.REPO_SUBFOLDER, 'config')
            config.parse_file(repo_config, skip_unreadable=False)

        return repo_root, config

    @classmethod
    def _merge_config(cls, config, sections=(), extra=None):
        merged = confhelpers.MergedConfig()
        if extra is not None:
            merged.add_options(extra)

        for section in sections:
            merged.add_options(config[section])

        merged.add_options(config['core'])

        return merged

    @classmethod
    def from_files(cls, repo_root=None, config_files=constants.CONFIG_FILES,
            sections=(), extra=None):
        """Build a Env from basic informations:

        - Path to a repository root
        - List of global configuration files to read
        - List of configuration sections to take into account
        - Dict of extra configuration values
        """

        repo_root, config = cls._read_config(repo_root=repo_root,
                config_files=config_files)

        repo = Repository(root=repo_root)
        repo.fill_from_config(config)

        config = cls._merge_config(config, sections=sections, extra=extra)

        return cls(root=repo_root, config=config, repository=repo)
