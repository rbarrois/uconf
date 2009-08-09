#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys

# Contains all log-related info

DEBUG = 0
NOTICE = 5
INFO = 10
WARN = 15
CRIT = 20

# Class holding current log level
class LogLevelHolder:
    logLevel = INFO

def setLogLevel(level):
    LogLevelHolder.logLevel = level

def getLogLevel():
    return LogLevelHolder.logLevel

def crit(msg):
    show(msg, CRIT)

def warn(msg):
    show(msg, WARN)

def info(msg):
    show(msg, INFO)

def notice(msg):
    show(msg, NOTICE)

def debug(msg):
    show(msg, DEBUG)

def show(msg,level):
    if level >= LogLevelHolder.logLevel :
        sys.stderr.write(msg + "\n")
