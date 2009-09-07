#!/usr/bin/python
# -*- coding: utf-8 -*-

import confmgr
from confmgr import log
from optparse import OptionParser

def parse(argv):
    """This function is used to parse the input from command line

    It expects the content of sys.argv[1:]."""
    usage = "usage: %prog [options] command"
    parser = OptionParser(usage)

    # Verbosity
    parser.set_defaults(verbosity = 0)
    parser.set_defaults(quietness = 0)
    parser.add_option("-v", "--verbose", action="count", dest="verbosity", help="Increase verbosity (several uses increase verbosity level)")
    parser.add_option("-q", "--quiet", action="count", dest="quietness", help="Increase quietness (several uses increase quietness level)")

    (options,args) = parser.parse_args(argv)

    if len(args) == 0:
        parser.error("You need to supply a command...")

    verbosity = options.verbosity - options.quietness

    cfmg = confmgr.ConfMgr(level = log.getLogLevelFromVerbosity(verbosity))

    if args[0] in cfmg.modules:
        cfmg.call(args[0], args[1:])
    else:
        parser.error("Command %s unknown." % args[0])
