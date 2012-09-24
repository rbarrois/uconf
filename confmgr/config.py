# -*- coding: utf-8 -*-

from __future__ import unicode_literals

"""Handle repository-wide configuration.

These settings only relate to the list of categories, files, ... registered in
the repository, regardless of current settings.
"""


import socket

# Local imports
from . import action_parser
from . import rule_parser


class ActionConfig(object):
    """Definition of the action for a file."""

    COPY = 'copy'
    SYMLINK = 'symlink'
    PARSE = 'parse'

    ACTIONS = (
        COPY,
        SYMLINK,
        PARSE,
    )

    def __init__(self, action, **options):
        if action not in self.ACTIONS:
            raise ValueError("Invalid action %s, choose one of %s" % (
                action, ', '.join(self.ACTIONS)))
        self.action = action
        self.options = options


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

    def iter_files(self, default_action=None):
        """Retrieve all active files for this view, including actions."""
        for file_rule, filename in self.base.file_rules:
            if file_rule.test(self.categories):
                action = self.base.file_actions.get(filename, default_action)
                yield filename, action


class Repository(object):
    """Holds repository configuration.

    Attributes:
        categories (str set): all categories
        files (str list): all managed files
        file_actions (dict(str => ActionConfig)): actions for files
        rule_lexer (rule_parser.RuleLexer): lexer to use for rule parsing
    """

    def __init__(self, *args, **kwargs):
        self.category_rules = []
        self.file_rules = []
        self.file_actions = {}
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
        for rule_text, filename in rules.items():
            rule = self.rule_lexer.get_rule(rule_text)
            self.file_rules.append((rule, filename))

    def _merge_file_actions(self, actions):
        for filename, action_text in actions.items():
            action, option_text = action_text.strip().split(' ', 1)
            options = self.action_lexer.parse(option_text)
            self.file_actions[filename] = ActionConfig(action, **options)

    def fill_from_config(self, config):
        self._merge_category_rules(config['categories'])
        self._merge_file_rules(config['files'])
        self._merge_file_actions(config['actions'])

