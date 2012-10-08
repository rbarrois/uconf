# coding: utf-8
# Copyright (c) 2010-2012 Raphaël Barrois


from __future__ import unicode_literals

import socket
import sys

from . import __version__
from . import config
from . import fs
from . import helpers
from .confhelpers import Default


class ConfmgrError(Exception):
    pass


class ConfigError(ConfmgrError):
    pass


class BaseCommand(object):
    """Base command object."""
    name = ''
    help = ''

    @classmethod
    def register_options(cls, parser):
        """Register command-specific options into an argparse subparser."""

    @classmethod
    def get_name(cls):
        """Retrieve the name of the command.

        Will try in order:
        - ``name`` attribute
        - lowercase class name, stripping the 'command' part.
        """
        if cls.name:
            return cls.name
        name = cls.__name__.lower()
        if name.endswith('command'):
            name = name[:-len('command')]
        return name

    @classmethod
    def get_help(cls):
        """Retrieve the help text for a command.

        If the ``help`` attribute is empty, use the class' docstring.
        """
        if cls.help:
            return cls.help
        else:
            return cls.__doc__

    required_config_fields = ()

    def __init__(self, env, parser):
        self.env = env
        self.parser = parser

        self.stdout = sys.stdout
        self.stderr = sys.stderr

        self.check_required_config()

    def check_required_config(self):
        for field in self.required_config_fields:
            if not self.env.isset(field):
                raise ConfigError("Field '%s' must be set, either in config files "
                    "or through command-line arguments." % field)

    def warning(self, message, *args):
        self.stderr.write(message % args)
        self.stderr.write('\n')
        if self.options.get('strict', False):
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


class WithRepoCommand(BaseCommand):
    """Enhanced base command class with list of rules already parsed."""

    def __init__(self, *args, **kwargs):
        super(WithRepoCommand, self).__init__(*args, **kwargs)

        initial_cats = self.env.getlist('initial',
            (socket.getfqdn(), socket.gethostname()))
        self.active_repository = self.env.get_active_repository(initial_cats)

    def _get_files(self, files):
        """Retrieve file config for a set of file names.

        If no filename was provided, return all files.
        """
        all_files = self.active_repository.iter_files(
            default_action=self.env.get('default_file_action', 'parse'))

        return helpers.filter_iter(all_files, files,
            key=lambda filename, _config: filename, empty_is_all=True)

    def _get_actions(self, files):
        for filename, file_config in self._get_files(files):
            action = file_config.get_action(filename, env=self.env)
            yield filename, action


class Make(WithRepoCommand):
    """Make one or more files."""

    name = 'make'
    help = "Build and install one or more files."

    required_config_fields = ('target',)

    @classmethod
    def register_options(cls, parser):
        parser.add_argument('files', nargs='*', default=Default(tuple()),
            help="Build selected files, all valid if empty.")
        super(Make, cls).register_options(parser)

    def run(self):
        categories = self.active_repository.categories
        for filename, action in self._get_actions(self.env.get('files')):
            self.info("Processing %s (%s)", filename, action.__class__.__name__)
            action.forward(categories)


class Back(WithRepoCommand):
    """Backport one or more files."""

    name = 'back'
    help = "Build and install one or more files."

    required_config_fields = ('target',)

    @classmethod
    def register_options(cls, parser):
        parser.add_argument('files', nargs='*', default=Default(tuple()),
            help="Backport selected files, all valid if empty.")
        super(Back, cls).register_options(parser)

    def run(self):
        categories = self.active_repository.categories
        for filename, action in self._get_actions(self.env.get('files')):
            self.info("Processing %s (%s)", filename, action.__class__.__name__)
            action.backward(categories)


class ListFiles(WithRepoCommand):
    name = 'files'
    help = "List all registered files"

    def run(self):
        for filename, _action in sorted(self.active_repository.iter_files()):
            self.info(filename)


class ListCategories(WithRepoCommand):
    name = 'categories'
    help = "List all active categories"

    def run(self):
        for category in sorted(self.active_repository.categories):
            self.info(category)


base_commands = [
    HelpCommand,
    VersionCommand,
    ListFiles,
    ListCategories,
    Make,
    Back,
]
