# coding: utf-8
# Copyright (c) 2010-2012 Raphaël Barrois


from __future__ import with_statement

import socket
import sys

from . import __version__
from . import config


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

    def __init__(self, options, repo_config, parser):
        self.options = options
        self.repo_config = repo_config
        self.parser = parser

        self.stdout = sys.stdout
        self.stderr = sys.stderr

    def warning(self, message, *args):
        self.stderr.write(message % args)
        self.stderr.write('\n')
        if self.options.strict:
            self.stderr.write("Strict mode: aborting.\n")
            raise SystemExit(1)

    def info(self, message, *args):
        self.stdout.write(message % args)
        self.stdout.write('\n')

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
        self.stdout.write('%(prog)s %(version)s\n' % dict(
            prog=self.parser.prog, version=__version__))


class WithFilesCommand(BaseCommand):
    """Enhanced base command class with list of rules already parsed."""

    def __init__(self, *args, **kwargs):
        super(WithFilesCommand, self).__init__(*args, **kwargs)
        self.repository = config.Repository()
        self.repository.fill_from_config(self.repo_config)

        initial_cats = self.options.get_tuple('initial',
            (socket.getfqdn(), socket.gethostname()))
        self.active_repository = self.repository.extract(initial_cats)


class ListFiles(WithFilesCommand):
    name = 'listfiles'
    help = "List all registered files"

    def run(self):
        for filename, _action in sorted(self.active_repository.iter_files()):
            self.stdout.write('- %s\n' % filename)


base_commands = [
    HelpCommand,
    VersionCommand,
    ListFiles,
]
