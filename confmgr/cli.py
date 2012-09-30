# coding: utf-8
# Copyright (c) 2010-2012 Raphaël Barrois


from __future__ import unicode_literals


"""Parse command-line arguments.

The CLI parsing is a three-step process:
    1) Parse a minimal set of configuration options:
        - verbosity
        - config file
        - repository root
    2) If a config file or a repository root is provided, read it and
       merge its "[core]" section into defaults for the next step
    3) Perform the full parsing
"""


import argparse
import os
import stat

from . import commands
from . import confhelpers
from . import __version__


DEFAULT_PREF_FILES = ('/etc/confmgr.conf', '~/.confmgrrc')


Default = confhelpers.Default


def get_absolute_path(path):
    return os.path.abspath(os.path.expanduser(path))


class CLI(object):
    """Command-line interface.

    Attributes:
        progname (str): name to use to refer to the program
        parser (argparse.ArgumentParser): list of available CLI args & options
        subparsers (argparse.SubParser): handles action-specific subparsers
    """

    def __init__(self, progname):
        self.progname = progname
        self.base_parser = self.make_base_parser(self.progname)
        self.parser = argparse.ArgumentParser(prog=self.progname,
            parents=[self.base_parser],
            argument_default=Default(None))
        self.subparsers = self.parser.add_subparsers(help="Commands")

        self.register_base_commands()

    # Options and parsers
    # -------------------

    def make_base_parser(self, progname):
        parser = argparse.ArgumentParser(prog=self.progname, add_help=False)
        parser.add_argument('--root', '-r', help="Set confmgr repository root")
        parser.add_argument('--repo-config', '-c',
            help="Use repository configuration file at REPO_CONFIG")
        parser.add_argument('--prefs', '-p', nargs='*', default=DEFAULT_PREF_FILES,
            help="Read user preferences from PREF files", metavar='PREF')
        parser.add_argument('--version', '-V', help="Display version", action='version',
            version='%(prog)s ' + __version__)
        return parser

    def register_options(self, parser):
        """Register global options"""
        parser.add_argument('--dry-run', '-n', help="Pretend to run the actions",
            action="store_true", default=False)
        parser.add_argument('--initial', '-i', nargs='*',
            help="Set alternate initial categories", default=Default(tuple()))
        parser.add_argument('--strict', help="Stop on warnings",
            action="store_true", default=False)
        parser.add_argument('--target', '-t', help="Write generated files to TARGET")

    # Registering commands
    # --------------------

    def register_command(self, command_class):
        """Register a new command from its class."""
        cmd_parser = self.subparsers.add_parser(command_class.get_name(),
            parents=[self.base_parser],
            help=command_class.get_help())
        self.register_options(cmd_parser)
        command_class.register_options(cmd_parser)
        cmd_parser.set_defaults(command=command_class)

    def register_base_commands(self):
        """Register all known, base commands."""
        for command_class in commands.base_commands:
            self.register_command(command_class)

    # Reading configuration
    # ----------------------

    def find_repo_root(self, start_folder):
        """Try to find a repository root starting in the current folder."""
        prev = None
        current = get_absolute_path(start_folder)
        while prev != current:
            maybe_config = os.path.join(current, '.confmgr')
            if os.access(maybe_config, os.F_OK):
                dirmode = os.stat(maybe_config).st_mode
                if stat.S_ISDIR(dirmode):
                    return current
            prev, current = current, os.path.dirname(current)

    def extract_config(self, base_args):
        """Retrieve and merge the various 'user-preference' config files."""

        # Merge preferences
        pref_files = base_args.prefs

        config = confhelpers.ConfigReader(
            multi_valued_sections=('files', 'categories', 'actions'))

        for pref_file in pref_files:
            filename = get_absolute_path(pref_file)
            if os.access(filename, os.R_OK):
                with open(filename, 'rt') as f:
                    config.parse(f, name_hint=filename)

        repo_root = repo_config_file = None

        # Fill repo_root/repo_config from CLI arguments
        if base_args.root:
            repo_root = get_absolute_path(base_args.root)
        if base_args.repo_config:
            repo_config_file = get_absolute_path(base_args.repo_config)

        # Try to fill repo_config_file/repo_root from each other
        if repo_config_file and not repo_root:
            repo_root = os.path.dirname(repo_config_file)
        if not repo_root:
            repo_root = self.find_repo_root(os.getcwd())
        if repo_root and not repo_config_file:
            repo_config_file = os.path.join(repo_root, '.confmgr', 'config')

        # Read configuration from repo config file, if available
        if repo_config_file and os.access(repo_config_file, os.R_OK):
            with open(repo_config_file, 'rt') as f:
                config.parse(f, name_hint=os.path.basename(repo_config_file))

        # Update base_args
        base_args.repo_config = config
        base_args.prefs = config
        base_args.root = repo_root

    def make_command_config(self, base_args, command_args, command_class):
        """Prepare the (merged) options pseudo-dict for a given command.

        Uses, in turn:
            - command-specific command line options
            - global command line options
            - command-specific configuration file options
            - global configuration file options
        """
        prefs = base_args.prefs

        return confhelpers.MergedConfig(
            confhelpers.DictNamespace(command_args),
            confhelpers.DictNamespace(base_args),
            confhelpers.NormalizedDict(prefs[command_class.get_name()]),
            confhelpers.NormalizedDict(prefs['core']),
        )

    # Running commands
    # ----------------

    def run_from_argv(self, argv):
        """Actually run the requested command from the argv."""
        # Fetch base settings
        base_args, _extra = self.base_parser.parse_known_args(argv)
        self.extract_config(base_args)

        # Add command-specific arguments
        args = self.parser.parse_args(argv)
        command_class = args.command

        # Merge all pref bits
        prefs = self.make_command_config(base_args, args, command_class)

        # Build and run the command
        cmd = command_class(prefs, base_args.repo_config, self.parser)
        return cmd.run()


def main(argv):
    """Run the prgoram."""
    progname = argv[0]
    args = argv[1:]
    cli = CLI(progname)
    return cli.run_from_argv(args)
