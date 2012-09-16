# coding: utf-8
# Copyright (c) 2010-2012 Raphaël Barrois


import argparse
import socket

from . import commands
from . import config


class CLI(object):
    """Command-line interface.

    Attributes:
        progname (str): name to use to refer to the program
        parser (argparse.ArgumentParser): list of available CLI args & options
        subparsers (argparse.SubParser): handles action-specific subparsers
    """

    def __init__(self, progname):
        self.progname = progname
        self.parser = argparse.ArgumentParser(prog=self.progname)
        self.subparsers = self.parser.add_subparsers(help="Commands")

        self.register_options(self.parser)
        self.register_base_commands()

    def register_options(self, parser):
        """Register global options"""
        parser.add_argument('--root', '-r', help="Set confmgr repository root",
            default='.')
        parser.add_argument('--dry-run', '-n', help="Pretend to run the actions",
            action="store_true", default=False)
        parser.add_argument('--initial', '-i', nargs='*',
            help="Set alternate initial categories")
        parser.add_argument('--target', '-t', help="Write generated files to TARGET")

    def register_command(self, command_class):
        """Register a new command."""
        cmd_parser = self.subparsers.add_parser(command_class.get_name(),
            help=command_class.get_help())
        command_class.register_options(cmd_parser)
        cmd_parser.set_defaults(command=command_class)

    def register_base_commands(self):
        for command_class in commands.base_commands:
            self.register_command(command_class)

    def build_config(self, args):
        """Build a config.Configuration() object from the passed-in options."""
        cfg = config.Configuration()

        if args.initial:
            cfg.add_initial_categories(args.initial)
        else:
            cfg.add_initial_categories([socket.getfqdn(), socket.gethostname()])

    def run_from_argv(self, argv):
        """Actually run the requested command from the argv."""
        args = self.parser.parse_args(argv)
        command_class = args.command
        cmd = command_class(config, args, self.parser)
        return cmd.run()


def main(argv):
    """Run the prgoram."""
    progname = argv[0]
    args = argv[1:]
    cli = CLI(progname)
    return cli.run_from_argv(args)
