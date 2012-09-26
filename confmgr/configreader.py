# coding: utf-8
# Copyright (c) 2010-2012 Raphaël Barrois


from __future__ import unicode_literals


"""Handle reading a configuration file in our manner.

This is a slight deviation from the 'configparser' module, since we have
unusual keys: "foo and bar: baz".
"""


import re


class BaseSection(object):
    def __init__(self, name):
        self.name = name
        self.entries = dict()

    def __iter__(self):
        return iter(self.items())

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.name)


class MultiValuedSection(BaseSection):
    """A section where each key may appear more than once."""

    def __setitem__(self, key, value):
        self.entries.setdefault(key, []).append(value)

    def items(self):
        for key, values in self.entries.items():
            for value in values:
                yield key, value


class SingleValuedSection(BaseSection):
    def __setitem__(self, key, value):
        self.entries[key] = value

    def items(self):
        return self.entries.items()


class ConfigReader(object):
    re_section_header = re.compile(r'^\[[\w._-]+\]$')
    re_blank_line = re.compile(r'^(#.*)?$')
    re_normal_line = re.compile(r'^([^:=]+)[:=](.*)$')

    def __init__(self, multi_valued_sections=()):
        self.sections = {}
        self.multi_valued_sections = multi_valued_sections
        self.current_section = self['core']

    def __getitem__(self, section_name):
        try:
            return self.sections[section_name]
        except KeyError:
            if section_name in self.multi_valued_sections:
                section = MultiValuedSection(section_name)
            else:
                section = SingleValuedSection(section_name)
            self.sections[section_name] = section
            return section

    def __iter__(self):
        return iter(self.sections)

    def enter_section(self, name):
        self.current_section = self[name]
        return self.current_section

    def parse(self, f, name_hint=''):
        self.enter_section('core')

        for lineno, line in enumerate(f):
            line = line.strip()
            if self.re_section_header.match(line):
                section_name = line[1:-1]
                self.enter_section(section_name)
            elif self.re_blank_line.match(line):
                continue
            else:
                match = self.re_normal_line.match(line)
                if not match:
                    raise ConfigSyntaxError("Invalid line %r at %s:%d" % (
                        line, name_hint or f, lineno))

                key, value = match.groups()
                self.current_section[key.strip()] = value.strip()

    def __repr__(self):
        return '<%s: %r>' % (self.__class__.__name__, self.sections)
