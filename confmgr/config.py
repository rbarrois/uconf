# -*- coding: utf-8 -*-

from __future__ import with_statement

# Global imports
import ConfigParser
import os
import re
import subprocess

# Local imports
from . import rule_parser


class ActionConfig(object):
    """Definition of the action for a file."""

    COPY = 'copy'
    SYMLINK = 'symlink'
    PARSE = 'parse'

    def __init__(self, action, target=None, **options):
        self.action = action
        self.target = target
        self.options = options


class Configuration(object):
    """Holds all configuration.

    Attributes:
        categories (str set): all categories
        files (str list): all managed files
        file_actions (dict(str => ActionConfig)): actions for files
        repo_root (str): absolute path of the repository root
        install_root (str): absolute path where files should be installed
        rule_lexer (rule_parser.RuleLexer): lexer to use for rule parsing
    """

    def __init__(self, *args, **kwargs):
        self.categories = frozenset()
        self.files = []
        self.file_actions = {}
        self.repo_root = None
        self.install_root = None
        self.rule_lexer = rule_parser.RuleLexer()

    def add_initial_categories(self, categories):
        self.categories |= frozenset(categories)

    def merge_category_rules(self, rules):
        for rule_text, extra_categories in rules:
            rule = self.rule_lexer.get_rule(rule_text)
            if rule.test(self.categories):
                self.categories |= frozenset(extra_categories)

    def merge_file_rules(self, rules):
        for rule_text, filename in rules:
            rule = self.rule_lexer.get_rule(rule_text)
            if rule.test(self.categories):
                self.files.append(filename)
