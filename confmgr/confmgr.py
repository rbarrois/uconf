#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys, os, optparse

# local imports
import log, config, actions

#version = @@VERSION@@
version = 0.1

# {{{1 __checkCfg
def __checkCfg(findRoot = True):
    cfg = config.getConfig()
    if not cfg.finalized:
        cfg.finalize()
    if findRoot:
        cfg.findRoot()
    return cfg

modules = ["init", "update", "build", "install", "diff", "check", "retrieve", "backport" ]

def printVersion():
    sys.stdout.write("""Confmgr %s
Copyright (C) 2009 XelNet

Written by Raphaël Barrois (Xelnor).\n""" % version)

def __init_parser(mth):
    parser = optparse.OptionParser(mth.__doc__, add_help_option = False)
    # Verbosity
    parser.set_defaults(verbosity = 0)
    parser.set_defaults(quietness = 0)
    parser.add_option("-h", "--help", action="help", help=optparse.SUPPRESS_HELP)
    parser.add_option("-v", "--verbose", action="count", dest="verbosity", help=optparse.SUPPRESS_HELP)
    parser.add_option("-q", "--quiet", action="count", dest="quietness", help=optparse.SUPPRESS_HELP)
    return parser

def __set_verb(opts):
    log.setLogLevel(log.getLogLevelFromVerbosity(opts.verbosity - opts.quietness))

# {{{1 __getMethod
def __getMethod(command):
    if command == "init":
        return cmd_init
    elif command == "update":
        return cmd_update
    elif command == "build":
        return cmd_build
    elif command == "install":
        return cmd_install
    elif command == "diff":
        return cmd_diff
    elif command == "check":
        return cmd_check
    elif command == "retrieve":
        return cmd_retrieve
    elif command == "backport":
        return cmd_backport
    else:
        log.crit("Unknown command %s." % command)
        exit(1)

# {{{1 getHelp
def getHelp(cmd):
    cmd = __getMethod(cmd).__name__
    doc = eval(cmd + '.__doc__')
    if doc == None:
        return ""
    else:
        return doc

# {{{1 call
def call(command, args):
    """Wrapper to confmgr.command(args)"""
    __checkCfg(False)
    mth = __getMethod(command)
    parser = eval('__parse_' + command)
    opts = None
    arg = None
    if parser != None:
        (opts, args) = parser(args)
    __set_verb(opts)
    return mth(opts, args)

# {{{1 commands

# {{{2 cmd_init
def __parse_init(args):
    """Parses args and returns (opts, args)"""
    parser = __init_parser(cmd_init)
    return parser.parse_args(args)

def cmd_init(opts, args):
    """Initialize a confmgr repo here"""
    cfg = __checkCfg(False)
    cfg.setRoot(os.getcwd())

# {{{2 cmd_update
def __parse_update(args):
    """Parses args and returns (opts, args)"""
    parser = __init_parser(cmd_update)
    return parser.parse_args(args)

def cmd_update(opts, args):
    """Update repo (through an update of the VCS)"""
    cfg = __checkCfg()

# {{{2 cmd_build
def __parse_build(args):
    """Parses args and returns (opts, args)"""
    parser = __init_parser(cmd_build)
    return parser.parse_args(args)

def cmd_build(opts, files):
    """Build all files needed for this host

    No options.
    Optionnally, a list of files to build can be given when calling."""
    cfg = __checkCfg()
    known_files = cfg.filerules.keys()

    # Load files given as arguments
    _files = []
    if len(files) > 0:
        for file in files:
            if file not in cfg.files:
                log.warn("No configuration for file %s, ignoring." % file)
            else:
                _files.append(file)
    else:
        _files = cfg.files

    for file in _files:
        if file not in known_files:
            log.warn("No rules given for file %s, ignoring." % file)
        else:
            rule = cfg.filerules[file]
            rule.build()

# {{{2 cmd_install
def __parse_install(args):
    """Parses args and returns (opts, args)"""
    parser = __init_parser(cmd_install)
    return parser.parse_args(args)

def cmd_install(opts, args):
    """Install all built files to their targets"""
    cfg = __checkCfg()
    known_files = cfg.filerules.keys()
    for file in cfg.files:
        if file not in known_files:
            log.warn("No rules given for file %s, ignoring." % file)
        else:
            rule = cfg.filerules[file]
            rule.install()

# {{{2 cmd_check
def __parse_check(args):
    """Parses args and returns (opts, args)"""
    parser = __init_parser(cmd_check)
    return parser.parse_args(args)

def cmd_check(opts, args):
    """Outputs list of files where there are diffs :
    - Between source and compiled
    - Between compiled and installed"""
    cfg = __checkCfg()
    known_files = cfg.filerules.keys()
    for file in cfg.files:
        if file not in known_files:
            log.warn("No rules given for file %s, ignoring." % file)
        else:
            rule = cfg.filerules[file]
            rule.check()

# {{{2 cmd_retrieve
def __parse_retrieve(args):
    """Parses args and returns (opts, args)"""
    parser = __init_parser(cmd_retrieve)
    return parser.parse_args(args)

def cmd_retrieve(opts, args):
    """Retrive installed files"""
    cfg = __checkCfg()
    known_files = cfg.filerules.keys()
    for file in cfg.files:
        if file not in known_files:
            log.warn("No rules given for file %s, ignoring." % file)
        else:
            rule = cfg.filerules[file]
            rule.retrieve()

# {{{2 cmd_backport
def __parse_backport(args):
    """Parses args and returns (opts, args)"""
    parser = __init_parser(cmd_backport)
    return parser.parse_args(args)

def cmd_backport(opts, args):
    """Backport modifications of retrieved files to their source versions"""
    cfg = __checkCfg()
    known_files = cfg.filerules.keys()
    for file in cfg.files:
        if file not in known_files:
            log.warn("No rules given for file %s, ignoring." % file)
        else:
            rule = cfg.filerules[file]
            rule.backport()

# {{{2 cmd_diff
def __parse_diff(args):
    """Parses args and returns (opts, args)"""
    parser = __init_parser(cmd_diff)
    return parser.parse_args(args)

def cmd_diff(opts, args):
    """Print diff between compiled files and installed versions."""
    cfg = __checkCfg()
    known_files = cfg.filerules.keys()
    for file in cfg.files:
        if file not in known_files:
            log.warn("No rules given for file %s, ignoring." % file)
        else:
            rule = cfg.filerules[file]
            rule.diff()


# {{{1 other stuff
def kikoo(self):
    log.info("COIN!!!")
    log.notice("Notice")
    log.debug("Debug...")
    log.warn("Warning")
    log.crit("42")
