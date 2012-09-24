# coding: utf-8
# Copyright (c) 2010-2012 Raphaël Barrois


from __future__ import unicode_literals


"""Handle reading a configuration file in our manner.

This is a slight deviation from the 'configparser' module, since we have
unusual keys: "foo and bar: baz".
"""


import re


class Section(object):
    def __init__(self, name):
        self.name = name
        self.d = dict()

    def __setitem__(self, key, value):
        self.d.setdefault(key, []).append(value)

    def items(self):
        for key, values in self.d.items():
            for value in values:
                yield (key, value)

    def __repr__(self):
        return '<Section %s>' % self.name


class ConfigReader(object):
    re_section_header = re.compile(r'^\[[\w._-]+\]$')
    re_blank_line = re.compile(r'^(#.*)?$')
    re_normal_line = re.compile(r'^([^:=]+)[:=](.*)$')

    def __init__(self):
        self.sections = {}
        self.current_section = self['core']

    def __getitem__(self, section_name):
        return self.sections.setdefault(section_name, {})

    def __iter__(self):
        return iter(self.sections)

    def enter_section(self, name):
        if name in self.sections:
            section = self.sections[name]
        else:
            section = Section(name)
            self.sections[name] = section
        self.current_section = section
        return section

    def parse(self, f, name_hint=''):
        self.enter_section('defaults')

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
