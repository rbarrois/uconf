#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys, os

# local imports
import log, config

cfg = config.getConfig()

def __checkCfg(findRoot = True):
    if not cfg.finalized:
        cfg.finalize()
    if findRoot:
        cfg.findRoot()

modules = ["init", "update", "build", "install", "diff", "check", "retrieve", "backport" ]

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


def call(command, args):
    """Wrapper to confmgr.command(args)"""
    __checkCfg(False)
    mth = __getMethod(command)
    if "-h" in args or "--help" in args:
        print mth.__doc__
    else:
        return mth(args)

def cmd_init(args):
    __checkCfg(False)
    cfg.setRoot(os.getcwd())

def cmd_update(args):
    __checkCfg()

def cmd_build(args):
    __checkCfg()
    known_files = cfg.filerules.keys()
    for file in cfg.files:
        if file not in known_files:
            log.warn("No rules given for file %s, ignoring." % file)
        else:
            rule = cfg.filerules[file]
            rule.build()

def cmd_install(args):
    __checkCfg()

def cmd_check(args):
    __checkCfg()

def cmd_retrieve(args):
    __checkCfg()

def kikoo(self):
    log.info("COIN!!!")
    log.notice("Notice")
    log.debug("Debug...")
    log.warn("Warning")
    log.crit("42")
