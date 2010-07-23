#!/usr/bin/env python2.6
# -*- coding: utf-8 -*-

import sys
import os

import core


def parse(argv):
    """This function is used to parse the input from command line

    It expects the content of sys.argv[1:]."""

    mods = ['version', 'help'] + core.modules
    mods.sort()
    cmds = dict()
    cmds['version'] = 'Print version information and exit'
    cmds['help'] = 'Print help message and exit'
    for md in core.modules:
        doc = core.getHelp(md)
        cmds[md] = doc.split('\n')[0]

    max_mod_len = 4 # for 'help'
    for mod in mods:
        max_mod_len = max(max_mod_len, len(mod))
    cmds_list = '\n'.join(
            "  %s\t%s" % (
                str.ljust(cmd, max_mod_len),
                cmds[cmd])
            for cmd in mods)

    short_help = """Usage: %s command [options] [args]

Global options :
  -V, --version  Print version information and exit
  -h, --help     Print this help message and exit
  -v, --verbose  Increase verbosity (several uses increase verbosity level)
  -q, --quiet    Decrease verbosity (several uses decrease verbosity level)\n""" % os.path.basename(sys.argv[0])

    full_help = """%s\nThe list of options and arguments for a command can be accessed through :
    %s help <command>

    %s\n""" % (
        short_help,
        os.path.basename(sys.argv[0]),
        cmds_list)

    if len(argv) > 0:
        if argv[0] in ('--version', '-version', 'version', '-V'):
            sys.stdout.write(core.getVersion())
            sys.exit(0)
        elif argv[0] in ('-h', '-help', '--help', 'help'):
            if len(argv) > 1:
                if argv[1] in core.modules:
                    sys.stdout.write(short_help)
                    sys.stdout.write("----------\nHelp for ``%s'' :\n\n" % argv[1])
                    core.call(argv[1], ['-h'] + argv[2:])
                else:
                    sys.stdout.write("Unknown command %s\n\n" % argv[1])
                    sys.stdout.write(short_help)
            else:
                sys.stdout.write(full_help)
            sys.exit(0)
        elif argv[0] in core.modules:
            core.call(argv[0], argv[1:])
        else:
            if len(argv) > 1:
                sys.stdout.write("Unknown command %s\n\n" % argv[1])
            sys.stdout.write(short_help)
            sys.exit(1)
