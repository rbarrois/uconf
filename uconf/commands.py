# -*- coding: utf-8 -*-
# Copyright (c) 2010-2013 Raphaël Barrois
# This software is distributed under the two-clause BSD license.


import logging
import os.path
import sys

from confutils import Default

from . import __version__
from . import helpers
from . import porcelain

logger = logging.getLogger(__name__)


class UConfError(Exception):
    pass


class ConfigError(UConfError):
    pass


class BaseCommand:
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
                raise ConfigError(
                    "Field '%s' must be set, either in config files "
                    "or through command-line arguments." % field,
                )

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


class Init(BaseCommand):
    name = 'init'
    help = "Setup a new uconf repository"

    required_config_fields = ('root',)

    def run(self):
        self.env.root = self.env.get('root')
        repo_fs = self.env.get_repo_fs()
        repo_fs.makedir(self.env.uconf_dir, recursive=True, allow_recreate=True)
        repo_fs.writelines(os.path.join(self.env.uconf_dir, 'config'), [])


class WithRepoCommand(BaseCommand):
    """Enhanced base command class with list of rules already parsed."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        initial_cats = self.env.getlist('initial', helpers.get_hostnames())
        self.active_repository = self.env.get_active_repository(initial_cats)

    def _get_files(self, files):
        """Retrieve file config for a set of file names.

        If no filename was provided, return all files.
        """
        all_files = self.active_repository.iter_files()

        return helpers.filter_iter(all_files, files, empty_is_all=True)


class Make(WithRepoCommand):
    """Make one or more files."""

    name = 'make'
    help = "Build and install one or more files."

    required_config_fields = ('target',)

    @classmethod
    def register_options(cls, parser):
        parser.add_argument(
            'files', nargs='*', default=Default(tuple()),
            help="Build selected files, all valid if empty.",
        )
        super().register_options(parser)

    def run(self):
        p = porcelain.MakeFile(self.env, self.active_repository)
        for filename in self._get_files(self.env.get('files')):
            try:
                p.handle(filename)
            except porcelain.PorcelainError as e:
                logger.exception("Error while handling %s: %r", filename, e)
                continue


class Back(WithRepoCommand):
    """Backport one or more files."""

    name = 'back'
    help = "Build and install one or more files."

    required_config_fields = ('target',)

    @classmethod
    def register_options(cls, parser):
        parser.add_argument(
            'files', nargs='*', default=Default(tuple()),
            help="Backport selected files, all valid if empty.",
        )
        super().register_options(parser)

    def run(self):
        p = porcelain.BackFile(self.env, self.active_repository)
        for filename in self._get_files(self.env.get('files')):
            try:
                p.handle(filename)
            except porcelain.PorcelainError as e:
                logger.exception("Error while handling %s: %r", filename, e)
                continue


class Diff(WithRepoCommand):
    """Check whether installed file are compatible with sources."""

    name = 'diff'
    help = "Compute diff between source and installed version of one or more files."

    required_config_fields = ('target',)

    @classmethod
    def register_options(cls, parser):
        parser.add_argument(
            'files', nargs='*', default=Default(tuple()),
            help="Compute diff of selected files, all valid if empty.",
        )
        super().register_options(parser)

    def run(self):
        p = porcelain.DiffFile(self.env, self.active_repository)
        for filename in self._get_files(self.env.get('files')):
            try:
                p.handle(filename)
            except porcelain.PorcelainError as e:
                logger.exception("Error while handling %s: %r", filename, e)
                continue


class BackDiff(WithRepoCommand):
    """Check whether source file are compatible with installed version."""

    name = 'backdiff'
    help = "Compute diff between source and installed version of one or more files."

    required_config_fields = ('target',)

    @classmethod
    def register_options(cls, parser):
        parser.add_argument(
            'files', nargs='*', default=Default(tuple()),
            help="Compute backward diff of selected files, all valid if empty.",
        )
        super().register_options(parser)

    def run(self):
        p = porcelain.BackDiffFile(self.env, self.active_repository)
        for filename in self._get_files(self.env.get('files')):
            try:
                p.handle(filename)
            except porcelain.PorcelainError as e:
                logger.exception("Error while handling %s: %r", filename, e)
                continue


class ImportFile(WithRepoCommand):
    name = 'import'
    help = "Import a new file into the repository"

    @classmethod
    def register_options(cls, parser):
        parser.add_argument('files', nargs='+', help="Add the selected files")
        parser.add_argument(
            '--categories', required=True,
            help="Import into the selected category",
        )
        parser.add_argument(
            '--action', nargs='?',
            help="Build with the selected action",
        )
        parser.add_argument(
            '--action-params', nargs='*', default=Default(()),
            help="Extra parameters for the selected action",
        )
        destination_group = parser.add_mutually_exclusive_group()
        destination_group.add_argument('--folder', help="Store the files in the given folder")
        super().register_options(parser)

    def run(self):
        action_params = list(self.env.get('action_params', ()))

        p = porcelain.ImportFiles(self.env, self.active_repository)
        p.handle(
            files=self.env.get('files'),
            categories=self.env.get('categories'),
            action=self.env.get('action'),
            action_params=action_params,
            folder=self.env.get('folder'),
        )


class RenameFile(WithRepoCommand):
    name = 'mv'
    help = "Rename a file within the repository"

    @classmethod
    def register_options(cls, parser):
        parser.add_argument('source', help="The file to rename")
        parser.add_argument('dest', help="The new path")
        super().register_options(parser)

    def run(self):
        source = self.env.get('source')
        dest = self.env.get('dest')
        p = porcelain.RenameFile(self.env, self.active_repository)
        p.handle(source, dest)


class ListFiles(WithRepoCommand):
    name = 'files'
    help = "List all registered files"

    def run(self):
        target = self.env.target
        for filename in sorted(self.active_repository.iter_files()):
            file_config = self.active_repository.get_file_config(filename)
            self.info("%s -> %s", filename, file_config.get_destination(filename, target))


class ListCategories(WithRepoCommand):
    name = 'categories'
    help = "List all active categories"

    def run(self):
        for category in sorted(self.active_repository.categories):
            self.info(category)


base_commands = [
    HelpCommand,
    VersionCommand,
    Init,
    ListFiles,
    ListCategories,
    ImportFile,
    RenameFile,
    Make,
    Back,
    Diff,
    BackDiff,
]
