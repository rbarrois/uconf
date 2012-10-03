# -*- coding: utf-8 -*-

from __future__ import unicode_literals, absolute_import

"""Handle repository-wide configuration.

These settings only relate to the list of categories, files, ... registered in
the repository, regardless of current settings.
"""


import fnmatch
import socket

from . import action_parser
from . import actions
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

