#!/usr/bin/env python2.6
# -*- coding: utf-8 -*-

# Global imports
import os
import re
import sys


# Local imports
import log
import config
import actions


def isSubdir(path, dir):
    """Tells whether a path is inside the repo root"""
    absdir = os.path.abspath(dir)
    abspath = os.path.normpath(os.path.join(dir, path))
    return (absdir == os.path.commonprefix([abspath, absdir]))

# {{{1 def getTime()
def getTime(file):
    cfg = config.getConfig()
    return os.path.getmtime(os.path.join(cfg.getRoot(), file))

# {{{1 def parseOptions
def parseOptions(options, def_options, file = ""):
    r"""Parses a string of options :
    a,b=c,d="e f,g",h='i\'j',k="l\"m",n=o\,p
    into :
    {'a':True, 'b': 'c', 'd': 'e f,g', 'h':'i\'j', 'k': 'l"m', 'n':'o,p'}
    valid forms are :
    blah (evals to blah = True)
    blah=true (or True, TRUE, TRuE, ...)
    blah=false (or False, FALSE, FalSe)
    blah=/bin/coin
    blah="/bin/coin -p"
    blah="/bin/coin 'a b.jpg'"
    blah="/bin/coin \"a b.jpg\""
    blah='/bin/coin "a b.jpg"'
    blah='/bin/coin \'a b.jpg\''
    blah="/bin/coin \"a \\\"b c\\\" d.jpg\""
    """
    opts = def_options
    cur = ""
    key = ""
    in_key = True
    escaping = False
    quoting = False
    quoter = ""
    for char in options:
        if escaping:
            cur += char
            escaping = False
        elif chr in ('\\'):
            if in_key:
                log.crit("Unexpected '\\' char in option key for {0}.".format(file), "ParseOptions")
                return
            escaping = True
        elif quoting:
            if char == quoter:
                quoting = False
                quoter = ''
            cur += char
        elif char in ('\'', '"'):
            if in_key:
                log.crit("Forbidden {c} char in option key for {f}.".format(c = char, f = file), "ParseOptions")
                return
            quoting = True
            quoter = char
            cur += char
        elif char == ',':
            if in_key:
                opts[key] = True
            elif cur.lower() == 'true':
                opts[key] = True
            elif cur.lower() == 'false':
                opts[key] = False
            else:
                opts[key] = cur
            key = ""
            cur = ""
            in_key = True
        elif char in ('='):
            if in_key:
                in_key = False
            else:
                log.crit("Unexpected '=' char in option key for {0}.".format(file), "ParseOptions")
                return
        else:
            if in_key:
                key += char
            else:
                cur += char
    if in_key:
        opts[key] = True
    elif quoting:
        log.crit("Error : unclosed quotes in option {o} for {f}.".format(o = key, f = file), "ParseOptions")
        # TODO : replace all sys.exit with exceptions
        sys.exit(2)
    elif escaping:
        log.crit("Error : missing char after \\ in option {o} for {f}".format(o = key, f = file), "ParseOptions")
        sys.exit(2)
    else:
        if cur.lower() == 'true':
            opts[key] = True
        elif cur.lower() == 'false':
            opts[key] = False
        else:
            opts[key] = cur
    return opts

# {{{1 class FileRule
class FileRule(object):
    def __init__(self, file, target, options = ''):
        self.file = file
        self.target = target
        self.parseOptions(options)
        log.debug("Added rule for '{f}' : target is '{t}', with options {o}".format(f = file, t = target, o = options), "Rules")
        log.fulldebug("Options are : {0}".format(repr)(self.options), "FileRule/Options")

    def parseOptions(self, options):
        cfg = config.getConfig()
        # First get default options from cfg, then add ones for the file, then merge CLI ones
        self.options = cfg.mergeCLIOptions(parseOptions(options, cfg.getRulesOptions(), self.file))

    # {{{2 Build
    def _buildAction(self):
        if 'def_build' not in self.options or self.options['def_build'] in ('', 'def_build'):
            log.debug("Applying def_build to {0}.".format(self.file), "Rules/Build")
            cfg = config.getConfig()
            src = os.path.join(cfg.getSrc(), self.file)
            return actions.def_build(src)
        else:
            act = self.options['def_build']
            if actions.actionExists('std' + act + 'action'):
                log.debug("Applying non-default build method {a} to {f}.".format(a = act, f = self.file), "Rules/Build")
                return eval('actions.' + actions.actionName('std' + act + 'action') + '()')
            else:
                log.debug("Calling {a} for building {f} to {t}".format(a = act, f = self.file, t = self.target), "Rules/Build")
                return actions.callCmdAction(act)

    def build(self):
        cfg = config.getConfig()
        # TODO : check 'config' timestamp as well
        src = os.path.join(cfg.getSrc(), self.file)
        dst = os.path.join(cfg.getDst(), self.file)
        act = self._buildAction()
        if not os.path.exists(src):
            log.crit("Source for {0} doesn't exist.".format(src), "Rules/Build")
            return
        src_time = getTime(src)
        if not os.path.exists(dst):
            log.notice("Target for {0} doesn't exist yet.".format(self.file), "Rules/Build")
            if not os.path.exists(os.path.dirname(dst)):
                log.notice("Folder for {0} doesn't exist, creating.".format(self.file), "Rules/Build")
                os.makedirs(os.path.dirname(dst))
            act.apply(src, dst)
        else:
            dst_time = getTime(dst)
            if dst_time < src_time:
                log.notice("Source file {s} has changed, updating {d}".format(s = self.file, d = self.target), "Rules/Build")
                act.apply(src, dst)
            else:
                log.notice("Target file {0} is more recent than source, skipping".format(self.target), "Rules/Build")

    # {{{2 Install
    def _installAction(self):
        if 'def_install' not in self.options or self.options['def_install'] in ('', 'def_install'):
            log.debug("Applying def_install to {0}.".format(self.file), "Rules/Install")
            cfg = config.getConfig()
            src = os.path.join(cfg.getDst(), self.file)
            return actions.def_install(src)
        else:
            act = self.options['def_install']
            if 'std_' + act in dir(actions):
                log.debug("Applying non-default install method {a} to {f}.".format(a = act, f = self.file), "Rules/Install")
                return eval('actions.std_' + act)
            else:
                log.debug("Calling {a} for installing {f} to {t}".format(a = act, f = self.file, t = self.target), "Rules/Install")
                return actions.callCmdAction(act)

    def install(self):
        cfg = config.getConfig()
        install_root = cfg.getInstallRoot()
        src = os.path.join(cfg.getDst(), self.file)
        dst = os.path.join(install_root, self.target)
        src_time = getTime(src)
        act = self._installAction()
        self._preinstall(src, dst)
        if not os.path.exists(dst):
            log.notice("Target for {0} doesn't exist yet.".format(src), "Rules/Install")
            act.apply(src, dst)
        else:
            dst_time = getTime(dst)
            if src_time < dst_time:
                log.warn("Target {t} has changed more recently than {s}.".format(s = src, t = dst), "Rules/Install")
            act.apply(src, dst)
        self._postinstall(src, dst)

    # {{{3 pre/post install actions
    def _preinstall(self, src, dst):
        if 'preinstall' not in self.options or self.options['preinstall'] == '':
            return
        cmd = self.options['preinstall']
        act = actions.customPreinstallAction(cmd)
        act.apply(src, dst)

    def _postinstall(self, src, dst):
        if 'postinstall' not in self.options or self.options['preinstall'] == '':
            return
        cmd = self.options['postinstall']
        act = actions.customPostinstallAction(cmd)
        act.apply(src, dst)

    # {{{2 retrieve
    def _retrieveAction(self):
        if 'def_retrieve' not in self.options or self.options['def_retrieve'] in ('', 'def_retrieve'):
            log.debug("Applying def_retrieve to {0}.".format(self.file), "Rules/Retrieve")
            cfg = config.getConfig()
            install_root = cfg.getInstallRoot()
            installed = os.path.join(install_root, self.target)
            src = os.path.join(cfg.getSrc(), self.file)
            dst = os.path.join(cfg.getDst(), self.file)
            return actions.def_retrieve(installed, src, dst)
        else:
            act = self.options['def_retrieve']
            if 'std_' + act in dir(actions):
                log.debug("Applying non-default retrieve method {a} to {f}.".format(a = act, f = self.file), "Rules/Retrieve")
                return eval('actions.std_' + act)
            else:
                log.debug("Calling {a} for retrieving {f} to {t}".format(a = act, f = self.file, t = self.target), "Rules/Retrieve")
                return actions.callCmdAction(act)

    def retrieve(self):
        cfg = config.getConfig()
        install_root = cfg.getInstallRoot()
        installed = os.path.join(install_root, self.target)
        src = os.path.join(cfg.getDst(), self.file)
        act = self._retrieveAction()
        log.info("Retrieving {0}".format(self.file), with_success = True)
        if not os.path.exists(src):
            log.warn("Trying to retrieve {0}, not available in repo !!".format(installed), "Rules/Retrieve")
        elif not os.path.exists(installed):
            return log.showActionResult(actions.ActionResult(success = False, msg = "Unable to retrieve non-existing file {0}".format(installed)))
        log.showActionResult(act.apply(installed, src))

    # {{{2 backport
    def _backportAction(self):
        if 'def_backport' not in self.options or self.options['def_backport'] in ('', 'def_backport'):
            log.debug("Applying def_backport to {0}.".format(self.file), "Rules/Backport")
            cfg = config.getConfig()
            dst = os.path.join(cfg.getDst(), self.file)
            src = os.path.join(cfg.getSrc(), self.file)
            return actions.def_backport(dst, src)
        else:
            act = self.options['def_backport']
            if actions.actionExists('std' + act + 'action'):
                log.debug("Applying non-default backport method {a} to {f}.".format(a = act, f = self.file), "Rules/Backport")
                return eval('actions.' + actions.actionName('std' + act + 'action') + '()' )
            else:
                log.debug("Calling {a} for backporting {f} to {t}".format(a = act, f = self.file, t = self.target), "Rules/Backport")
                return actions.callCmdAction(act)

    def backport(self):
        cfg = config.getConfig()
        src = os.path.join(cfg.getSrc(), self.file)
        dst = os.path.join(cfg.getDst(), self.file)
        act = self._backportAction()
        log.info("Backporting {0}".format(self.file), with_success = True)
        if not os.path.exists(src):
            log.warn("Trying to backport to {0}, which doesn't exist !".format(src), "Rules/Backport")
        elif not os.path.exists(dst):
            return log.showActionResult(actions.ActionResult(success = False, msg = "Unable to backport non-existing file {0}".format(dst)))
        else:
            time_src = getTime(src)
            time_dst = getTime(dst)
            if time_src > time_dst:
                log.warn("Warning : backporting {dst} onto {src} which changed more recently".format(src = src, dst = dst), "Rules/Backport")
        log.showActionResult(act.apply(dst, src))

    # {{{2 diff
    def _diffAction(self):
        if 'def_diff' not in self.options or self.options['def_diff'] in ('', 'def_diff'):
            log.debug("Applying def_diff to {0}.".format(self.file), "Rules/Diff")
            return actions.def_diff()
        else:
            act = self.options['def_diff']
            if 'std_' + act in dir(actions):
                log.debug("Applying non-default diff method {a} to {f}.".format(a = act, f = self.file), "Rules/Diff")
                return eval('actions.std_' + act)
            else:
                log.debug("Calling {a} for diffing {f} with {t}".format(a = act, f = self.file, t = self.target), "Rules/Diff")
                return actions.callCmdAction(act)

    def diff(self):
        cfg = config.getConfig()
        install_root = cfg.getInstallRoot()
        src = os.path.join(cfg.getDst(), self.file)
        dst = os.path.join(install_root, self.target)
        if not os.path.exists(src):
            log.warn("Trying to find diffs for {0}, which doesn't exist !".format(self.file), "Rules/Diff")
        elif not os.path.exists(dst):
            log.warn("Installed file {0} doesn't exist !".format(dst), "Rules/Diff")
        act = self._diffAction()
        log.info("Running diff for {0}".format(self.file), with_success = True)
        log.showActionResult(act.apply(src, dst))

    # {{{2 check
    def _checkAction(self):
        """Returns the action for checking : generally def_check"""
        if 'def_check' not in self.options or self.options['def_check'] in ('', 'def_check'):
            log.debug("Applying def_check to {0}.".format(self.file), "Rules/Check")
            return actions.def_check()
        else:
            act = self.options['def_check']
            if 'std_' + act in dir(actions):
                log.debug("Applying non-default check method {a} to {f}.".format(a = act, f = self.file), "Rules/Check")
                return eval('actions.std_' + act)
            else:
                log.debug("Calling {a} for checking {f} with {t}".format(a = act, f = self.file, t = self.target), "Rules/Check")
                return actions.callCmdAction(act)

    def check(self):
        cfg = config.getConfig()
        install_root = cfg.getInstallRoot()
        src = os.path.join(cfg.getSrc(), self.file)
        dst = os.path.join(cfg.getDst(), self.file)
        installed = os.path.join(install_root, self.target)
        if not os.path.exists(src):
            log.warn("Source file {0} is missing !!".format(src), "Rules/Check")
        if not os.path.exists(dst):
            log.warn("Compiled file {0} is missing !!".format(dst), "Rules/Check")
        if not os.path.exists(installed):
            log.warn("Installed file {0} is missing !!".format(installed), "Rules/Check")
        log.info("Checking {0}...".format(src), with_success = True)
        act = self._checkAction()
        log.showActionResult(act.apply(src, dst, installed))



# {{{1 def filenameSplit(txt, amount)
def filenameSplit(txt, amount = 0):
    """Splits a text into at most amount filenames strings

    if amount is 0 (default), the string will be split into every non-empty filename encountered.

    '\\ ' is converted to a space, '\\\\' to '\\'
    '\\x' with x neither ' ' nor '\\' is simply removed.

    If amount is non zero, all \\ in last part won't be interpreted."""
    parts = []
    prev_is_backslash = False
    raw = False
    cur = ""
    for x in txt:
        if raw:
            cur += x
        elif x == '\\':
            if prev_is_backslash:
                cur += '\\'
                prev_is_backslash = False
            else:
                prev_is_backslash = True
        elif x == ' ':
            if prev_is_backslash:
                cur += ' '
            elif amount == 0 or len(parts) < amount - 1 :
                if cur != "":
                    parts.append(cur)
                    cur = ""
            else:
                # amount != 0 && len(parts) == amount - 1 => we are reading last item
                raw = True
                cur += ' '
            prev_is_backslash = False
        elif x == '\t':
            prev_is_backslash = False
            if amount == 0 or len(parts) < amount - 1:
                if cur != "":
                    parts.append(cur)
                    cur = ""
            else:
                raw = True
                cur += '\t'
        else:
            prev_is_backslash = False
            cur += x
    if cur != "":
        parts.append(cur)
    return parts


# {{{1 def parse_cplx_pre(pre)
def parse_cplx_pre(pre):
    """Parses a complex precondition
    and returns a "CplxApplier" object

    expects an expression of the form :
    (a and not b) or (c && ! (d || e))"""

    log.debug("Parsing {0}".format(pre), "RuleParser")

    split_re = '[ \t]*([()!]|[ \t]and[ \t]|[ \t]or[ \t]|[ \t]not[ \t]|&&|\|\|)[ \t]*'
    rawparts = re.split(split_re, pre)
    parts = []
    for part in rawparts:
        cln_part = part.strip()
        if len(cln_part) == 0:
            continue
        if cln_part == '&&':
            cln_part = 'and'
        elif cln_part == '||':
            cln_part = 'or'
        elif cln_part == '!':
            cln_part = 'not'
        parts.append(cln_part)
    return CplxApplier(rule = parts)

# {{{1 class CplxApplier
class CplxApplier(object):
    """Holds what is needed to apply a complex rule"""
    def __init__(self, rule):
        self.rule = rule
        self.__cur_cats = set()

    def _has(self, cat):
        return (cat in self.__cur_cats)

    def apply(self, cats):
        """Applies the rule to a list of cats"""
        self.__cur_cats = cats

        # Convert tokens to use allcats[cat] instead of cat
        tokens = []
        for token in self.rule:
            if token not in ("and", "or", "not", "(", ")"):
                tokens.append("self._has('" + token + "')")
            else:
                tokens.append(token)

        # Apply the rule
        log.debug("Rule is {0}".format(" ".join(tokens)), "RuleParser")
        res = eval(" ".join(tokens))
        self.__cur_cats = set()
        return res

