# -*- coding: utf-8 -*-

from __future__ import with_statement

# Global imports
import ConfigParser
import os
import re
import subprocess

# Local imports
import log
import misc


class Configuration(object):
    """Holds all configuration."""

    def __init__(self, *args, **kwargs):
        self.categories = frozenset()
        self.files = []
        self.repo_root = None
        self.install_root = None

    def add_initial_categories(self, categories):
        self.categories |= frozenset(categories)

    def merge_category_rules(self, rules):
        for rule_text, extra_categories in rules:
            rule = parser.Rule(rule_text)
            if rule.test(self.categories):
                self.categories |= frozenset(extra_categories)

    def merge_file_rules(self, rules):
        for rule_text, filename in rules:
            rule = parser.Rule(rule_text)
            if rule.test(self.categories):
                self.files.append(filename)












