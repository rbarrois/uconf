#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys,commands,os

# Contains all log-related info

FULLDEBUG = -5
DEBUG = 0
NOTICE = 5
INFO = 10
WARN = 15
CRIT = 20

# Read args to set initial debug level
def setInitialLogLevel():
    verb = 0
    # Skip args 0 (binary name) and 1 (command)
    for arg in sys.argv[2:]:
        if arg == "-v":
            verb += 1
        elif arg == "-q":
            verb -= 1
        else:
            break
    setLogLevel(getLogLevelFromVerbosity(verb))

# Class holding current log level
class LogLevelHolder:
    logLevel = INFO
    success_level = INFO
    last_width = 0
    have_color = True

def setLogLevel(level):
    if level <= CRIT:
        LogLevelHolder.logLevel = level

def getLogLevelFromVerbosity(verb):
    """Converts a 'verbosity' level to a log level

    Verbosity ranges from -2 (Only CRIT) to +2 (All to DEBUG)"""
    return (10 - (5 * verb))

def getLogLevel():
    return LogLevelHolder.logLevel

def crit(msg, module = None, with_success = False):
    show(msg, CRIT, module, with_success)

def warn(msg, module = None, with_success = False):
    show(msg, WARN, module, with_success)

def info(msg, module = None, with_success = False):
    show(msg, INFO, module, with_success)

def notice(msg, module = None, with_success = False):
    show(msg, NOTICE, module, with_success)

def debug(msg, module = None, with_success = False):
    show(msg, DEBUG, module, with_success)

def fulldebug(msg, module = None, with_success = False):
    show(msg, FULLDEBUG, module, with_success)

# {{{1 Success / fail
__esc_seq = "\x1b["
__colors = dict()
__colors["reset"]   = __esc_seq + "39;49;00m"
__colors["red"]     = __esc_seq + "31m"
__colors["green"]   = __esc_seq + "32m"
__colors["yellow"]  = __esc_seq + "33m"
__colors["blue"]    = __esc_seq + "34m"
__colors["magenta"] = __esc_seq + "35m"
__colors["cyan"]    = __esc_seq + "36m"
__colors["white"]   = __esc_seq + "37m"
__colors["grey"]    = __esc_seq + "30;01m"

__module_colors = dict()
__module_colors[FULLDEBUG] = "grey"
__module_colors[DEBUG] = "blue"
__module_colors[NOTICE] = "cyan"
__module_colors[INFO] = ""
__module_colors[WARN] = "yellow"
__module_colors[CRIT] = "red"

def __colorize(code, txt):
    if LogLevelHolder.have_color and code in __colors.keys():
        return __colors[code] + txt + __colors["reset"]
    else:
        return txt

def __screensize():
    """Returns size of screen"""
    if not sys.stdout.isatty():
        return -1, -1
    st, out = commands.getstatusoutput('stty size')
    if st == os.EX_OK:
        parts = out.split()
        if len(parts) == 2:
            return int(parts[0]), int(parts[1])
    return -1, -1

def success():
    if LogLevelHolder.success_level >= LogLevelHolder.logLevel:
        __print_status(success = True)

def fail():
    if LogLevelHolder.success_level >= LogLevelHolder.logLevel:
        __print_status(success = False)

def __print_status(success = True):
    lines, cols = __screensize()
    last_width = LogLevelHolder.last_width
    if success:
        msg = __colorize("blue", "[ ") + __colorize("green", "ok") + __colorize("blue", " ]")
    else:
        msg = colorize("blue", "[ ") + colorize("red", "!!") + colorize("blue", "]")
    padding = " " * (cols - last_width - 6)
    sys.stderr.write(padding + msg + "\n")

def show(msg, level, module = None, with_success = False):
    if level >= LogLevelHolder.logLevel :
        if module != None:
            color = __module_colors[level]
            msg = __colorize("magenta", "[") + __colorize(color, module) + __colorize("magenta", "]") + " " + msg
        sys.stderr.write(msg)
        if with_success:
            LogLevelHolder.success_level = level
            LogLevelHolder.last_width = len(msg.decode('utf-8'))
        else:
            sys.stderr.write("\n")


setInitialLogLevel()
