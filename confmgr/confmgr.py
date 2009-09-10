#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys, os

# local imports
import log, config, parsers


# {{{1 __checkCfg
def __checkCfg(findRoot = True):
    cfg = config.getConfig()
    if not cfg.finalized:
        cfg.finalize()
    if findRoot:
        cfg.findRoot()
    return cfg

modules = ["init", "update", "build", "install", "diff", "check", "retrieve", "backport" ]

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
        return cmd_install
    elif command == "check":
        return cmd_check
    elif command == "retrieve":
        return cmd_retrieve
    else:
        log.crit("Unknown command %s." % command)
        exit(1)

# {{{1 call
def call(command, args):
    """Wrapper to confmgr.command(args)"""
    __checkCfg(False)
    mth = __getMethod(command)
    if "-h" in args or "--help" in args:
        print mth.__doc__
    else:
        return mth(args)

# {{{1 commands

# {{{2 cmd_init
def cmd_init(args):
    cfg = __checkCfg(False)
    cfg.setRoot(os.getcwd())

# {{{2 cmd_update
def cmd_update(args):
    cfg = __checkCfg()

# {{{2 cmd_build
def cmd_build(args):
    cfg = __checkCfg()
    known_files = cfg.filerules.keys()
    for file in cfg.files:
        if file not in known_files:
            log.warn("No rules given for file %s, ignoring." % file)
        else:
            rule = cfg.filerules[file]
            rule.build()

# {{{2 cmd_install
def cmd_install(args):
    cfg = __checkCfg()

# {{{2 cmd_check
def cmd_check(args):
    cfg = __checkCfg()

# {{{2 cmd_retrieve
def cmd_retrieve(args):
    cfg = __checkCfg()

# {{{1 other stuff
def kikoo(self):
    log.info("COIN!!!")
    log.notice("Notice")
    log.debug("Debug...")
    log.warn("Warning")
    log.crit("42")
