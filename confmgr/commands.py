# coding: utf-8
# Copyright (c) 2010-2012 Raphaël Barrois


from __future__ import with_statement


class BaseCommand(object):
    """Base command object."""
    name = ''
    help = ''

    @classmethod
    def register_options(cls, parser):
        """Register command-specific options into an argparse subparser."""

    @classmethod
    def get_name(cls):
        if cls.name:
            return cls.name
        name = cls.__name__.lower()
        if name.endswith('command'):
            name = name[:-len('command')]
        return name

    @classmethod
    def get_help(cls):
        if cls.help:
            return cls.help
        else:
            return cls.__doc__

    def __init__(self, config, options, parser):
        self.config = config
        self.options = options
        self.parser = parser

    def run(self):
        """Run the actual command."""
        pass


class HelpCommand(BaseCommand):
    name = 'help'
    help = "List of options and commands"

    def run(self):
        self.parser.print_help()


class VersionCommand(BaseCommand):
    name = 'version'
    help = "Display the current version number"

    def run(self):
        self.parser.print_version()


base_commands = [
    HelpCommand,
    VersionCommand,
]
