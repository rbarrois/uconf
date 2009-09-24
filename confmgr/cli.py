#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys

import confmgr
from confmgr import log
from optparse import OptionParser

def parse(argv):
    """This function is used to parse the input from command line

    It expects the content of sys.argv[1:]."""

    if len(argv) > 0 and argv[0] in ('--version', '-version', 'version', '-V'):
        confmgr.printVersion()
        sys.exit(1)

    cmds = ['version', 'help'] + confmgr.modules[:]
    cmds.sort()
    usage = ("""usage: %%prog [options] command [cmd-opts] [cmd-args]

Where command is one of %s

The list of options and arguments for a command can be accessed through :
    %%prog [options] command -h""" % ', '.join(cmds))
    parser = OptionParser(usage)

    # Verbosity
    parser.set_defaults(verbosity = 0)
    parser.set_defaults(quietness = 0)
    parser.add_option("-V", "--version", action="count", dest="version", help="print version message and exit")
    parser.add_option("-v", "--verbose", action="count", dest="verbosity", help="Increase verbosity (several uses increase verbosity level)")
    parser.add_option("-q", "--quiet", action="count", dest="quietness", help="Increase quietness (several uses increase quietness level)")

    (options,args) = parser.parse_args(argv)

    if len(args) == 0:
        parser.error("You need to supply a command...")

    verbosity = options.verbosity - options.quietness

    log.setLogLevel(log.getLogLevelFromVerbosity(verbosity))

    if args[0] in confmgr.modules:
        confmgr.call(args[0], args[1:])
    else:
        parser.error("Command %s unknown." % args[0])
