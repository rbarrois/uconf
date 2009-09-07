#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys

# local imports
import log, config, core

class ConfMgr:
    modules = ["init", "update", "build", "install", "diff", "check", "retrieve", "backport" ]

    def __init__(self, level = log.INFO):
        log.setLogLevel(level)
        self.config = config.Config()

    def call(self, command, args):
        # Find root of current path
        if command not in ("init"):
            self.config.findRoot()
        else:
            import os
            self.config.setRoot(os.getcwd())

        self.config.prepare()

        if command in ("init", "update"):
            import rcs
            rcs = rcs.Rcs(self.config)
            rcs._call(command, args)
        elif command in ("build"):
            import builder
            bldr = builder.Builder(self.config)
            bldr._call(command, args)
        elif command in ("install"):
            import installer
            istlr = installer.Installer(self.config)
            istlr._call(command, args)
        elif command in ("diff", "check"):
            import differ
            dfr = differ.Differ(self.config)
            dfr._call(command, args)
        elif command in ("retrieve"):
            import retriever
            rtrvr = retriever.Retriever(self.config)
            rtrvr._call(command, args)
        elif command in ("backport"):
            import backporter
            bptr = backporter.Backporter(self.config)
            bptr._call(command, args)
        else:
            return
        return

    def kikoo(self):
        log.info("COIN!!!")
        log.notice("Notice")
        log.debug("Debug...")
        log.warn("Warning")
        log.crit("42")
