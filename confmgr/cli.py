#!/usr/bin/env python2.6
# -*- coding: utf-8 -*-

import sys, os

import confmgr

def parse(argv):
    """This function is used to parse the input from command line

    It expects the content of sys.argv[1:]."""

    mods = ['version', 'help'] + confmgr.modules
    mods.sort()
    cmds = dict()
    cmds['version'] = 'Print version information and exit'
    cmds['help'] = 'Print help message and exit'
    for md in confmgr.modules:
        doc = confmgr.getHelp(md)
        cmds[md] = doc.split('\n')[0]

    max_mod_len = 4 # for 'help'
    for mod in mods:
        max_mod_len = max(max_mod_len, len(mod))
    cmds_list = '\n'.join(
            "  {cmd}\t{help}".format(
                cmd = str.ljust(cmd, max_mod_len),
                help = cmds[cmd])
            for cmd in mods)

    short_help = """Usage: {prog} command [options] [args]

Global options :
  -V, --version  Print version information and exit
  -h, --help     Print this help message and exit
  -v, --verbose  Increase verbosity (several uses increase verbosity level)
  -q, --quiet    Decrease verbosity (several uses decrease verbosity level)\n""".format(
          prog=os.path.basename(sys.argv[0]) )

    full_help = """{short}\nThe list of options and arguments for a command can be accessed through :
    {prog} help <command>

    {cmds}\n""".format(
        short = short_help,
        prog = os.path.basename(sys.argv[0]),
        cmds = cmds_list)

    if len(argv) > 0:
        if argv[0] in ('--version', '-version', 'version', '-V'):
            confmgr.printVersion()
            sys.exit(0)
        elif argv[0] in ('-h', '-help', '--help', 'help'):
            if len(argv) > 1:
                if argv[1] in confmgr.modules:
                    sys.stdout.write(short_help)
                    sys.stdout.write("----------\nHelp for ``{module}'' :\n\n".format(module=argv[1]))
                    confmgr.call(argv[1], ['-h'] + argv[2:])
                else:
                    sys.stdout.write("Unknown command {0}\n\n".format(argv[1]))
                    sys.stdout.write(short_help)
            else:
                sys.stdout.write(full_help)
            sys.exit(0)
        elif argv[0] in confmgr.modules:
            confmgr.call(argv[0], argv[1:])
        else:
            if len(argv) > 1:
                sys.stdout.write("Unknown command {0}\n\n".format(argv[1]))
            sys.stdout.write(short_help)
            sys.exit(1)
