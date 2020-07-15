# -*- coding: utf-8 -*-
# Copyright (c) 2010-2013 Raphaël Barrois
# This software is distributed under the two-clause BSD license.


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
import logging
import os

import confutils

from . import commands
from . import config
from . import constants
from . import __version__


Default = confutils.Default


class CLI:
    """Command-line interface.

    Attributes:
        progname (str): name to use to refer to the program
        parser (argparse.ArgumentParser): list of available CLI args & options
        subparsers (argparse.SubParser): handles action-specific subparsers
    """

    def __init__(self, progname):
        self.progname = progname
        self.parser = self.make_base_parser(self.progname)
        self.subparsers = self.parser.add_subparsers(help="Commands", dest='subcommand')

        self.register_base_commands()

    # Options and parsers
    # -------------------

    def make_base_parser(self, progname):
        parser = argparse.ArgumentParser(prog=self.progname, argument_default=Default(None))
        parser.add_argument(
            '--version', '-V', help="Display version", action='version',
            version='%(prog)s ' + __version__)
        return parser

    def register_options(self, parser):
        """Register global options"""
        parser.add_argument('--root', '-r', help="Set uconf repository root")
        parser.add_argument('--config-dir', '-c', help="Use uconf config dir CONFIG_DIR")
        parser.add_argument(
            '--prefs', '-p', nargs='*', default=constants.CONFIG_FILES,
            help="Read user preferences from PREF files", metavar='PREF',
        )
        parser.add_argument(
            '--version', '-V', action='version',
            version='%(prog)s ' + __version__, help="Display version",
        )
        parser.add_argument(
            '--dry-run', '-n', action='store_true',
            default=Default(False), help="Pretend to run the actions",
        )
        parser.add_argument(
            '--initial', '-i', nargs='*',
            help="Set alternate initial categories", default=Default(tuple()),
        )
        parser.add_argument(
            '--strict', help="Stop on warnings", action="store_true",
            default=Default(False),
        )
        parser.add_argument(
            '--target', '-t',
            default=Default(''), help="Write generated files to TARGET",
        )

    # Registering commands
    # --------------------

    def register_command(self, command_class):
        """Register a new command from its class."""
        cmd_parser = self.subparsers.add_parser(
            command_class.get_name(),
            help=command_class.get_help(),
        )

        self.register_options(cmd_parser)
        command_class.register_options(cmd_parser)
        cmd_parser.set_defaults(command=command_class)

    def register_base_commands(self):
        """Register all known, base commands."""
        for command_class in commands.base_commands:
            self.register_command(command_class)

    # Reading configuration
    # ----------------------

    def make_command_config(self, args, command_class):
        """Prepare the (merged) options pseudo-dict for a given command.

        Uses, in turn:
            - command-specific command line options
            - global command line options
            - command-specific configuration file options
            - global configuration file options
        """
        return config.Env.from_files(
            repo_root=args.root or os.getcwd(),
            sections=(command_class.get_name(),),
            extra=confutils.DictNamespace(args),
        )

    # Logging
    # -------

    def setup_logging(self):
        """Set up a minimal logging configuration."""
        root_logger = logging.getLogger()
        handler = logging.StreamHandler()
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)

    # Running commands
    # ----------------

    def run_from_argv(self, argv):
        """Actually run the requested command from the argv."""
        self.setup_logging()
        # Add command-specific arguments
        args = self.parser.parse_args(argv)
        command_name = args.subcommand
        if command_name is None:
            self.parser.print_help()
            return
        command_class = args.command

        # Merge all pref bits
        env = self.make_command_config(args, command_class)

        # Build and run the command
        cmd = command_class(env, self.parser)
        return cmd.run()


def main(argv):
    """Run the prgoram."""
    progname = argv[0]
    args = argv[1:]
    cli = CLI(progname)
    return cli.run_from_argv(args)
