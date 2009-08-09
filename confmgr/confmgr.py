#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys

# local imports
import log

class ConfMgr:
    def __init__(self, level = log.INFO):
        log.setLogLevel(level)

    def kikoo(self):
        log.info("COIN!!!")
        log.notice("Notice")
        log.debug("Debug...")
        log.warn("Warning")
        log.crit("42")
