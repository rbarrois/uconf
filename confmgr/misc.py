#!/usr/bin/python
# -*- coding: utf-8 -*-

# Global imports
import os, re

# Local imports
import log, config, actions

def isSubdir(path, dir):
    """Tells whether a path is inside the repo root"""
    absdir = os.path.abspath(dir)
    abs = os.path.normpath(os.path.join(dir, path))
    return (absdir == os.path.commonprefix([abs, absdir]))

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
    for chr in options:
        if escaping:
            cur += chr
            escaping = False
        elif chr in ('\\'):
            if in_key:
                log.crit("Unexpected '\\' char in option key for %s." % file, "ParseOptions")
                return
            escaping = True
        elif quoting:
            if chr == quoter:
                quoting = False
                quotter = ''
            cur += chr
        elif chr in ('\'', '"'):
            if in_key:
                log.crit("Forbidden %s char in option key for %s." % (chr, file), "ParseOptions")
                return
            quoting = True
            quotter = chr
            cur += chr
        elif chr == ',':
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
        elif chr in ('='):
            if in_key:
                in_key = False
            else:
                log.crit("Unexpected '=' char in option key for %s." % file, "ParseOptions")
                return
        else:
            if in_key:
                key += chr
            else:
                cur += chr
    if in_key:
        opts[key] = True
    elif quoting:
        log.crit("Error : unclosed quotes in option %s for %s." % (key, file), "ParseOptions")
        sys.exit(2)
    elif escaping:
        log.crit("Error : missing char after \\ in option %s for %s" % (key, file), "ParseOptions")
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
class FileRule:
    def __init__(self, file, target, options = ''):
        self.file = file
        self.target = target
        self.parseOptions(options)
        log.debug("Added rule for '%s' : target is '%s', with options %s" % (file, target, options), "Rules")
        log.fulldebug("Options are : %s" % repr(self.options), "FileRule/Options")

    def parseOptions(self, options):
        cfg = config.getConfig()
        # First get default options from cfg, then add ones for the file, then merge CLI ones
        self.options = cfg.mergeCLIOptions(parseOptions(options, cfg.getRulesOptions(), self.file))

    # {{{2 Build
    def _buildAction(self):
        if not self.options.has_key("def_build") or self.options['def_build'] in ('', 'def_build'):
            log.debug("Applying def_build to %s." % self.file, "Rules/Build")
            cfg = config.getConfig()
            root = cfg.getRoot()
            src = os.path.join(root, 'src', self.file)
            return actions.def_build(src)
        else:
            act = self.options['def_build']
            if 'std_' + act in dir(actions):
                log.debug("Applying non-default build method %s to %s." % (act, self.file), "Rules/Build")
                return eval('actions.std_' + act)
            else:
                log.debug("Calling %s for building %s to %s" % (act, self.file, self.target), "Rules/Build")
                return actions.call_cmd(act)

    def build(self):
        cfg = config.getConfig()
        # TODO : check 'config' timestamp as well
        root = cfg.getRoot()
        src = os.path.join(root, 'src', self.file)
        dst = os.path.join(root, 'dst', self.file)
        act = self._buildAction()
        if not os.path.exists(src):
            log.crit("Source for %s doesn't exist." % src, "Rules/Build")
            return
        src_time = getTime(src)
        if not os.path.exists(dst):
            log.notice("Target for %s doesn't exist yet." % self.file, "Rules/Build")
            if not os.path.exists(os.path.dirname(dst)):
                log.notice("Folder for %s doesn't exist, creating." % self.file, "Rules/Build")
                os.makedirs(os.path.dirname(dst))
            act(src, dst)
        else:
            dst_time = getTime(dst)
            if dst_time < src_time:
                log.notice("Source file %s has changed, updating %s" % (self.file, self.target), "Rules/Build")
                act(src, dst)
            else:
                log.notice("Target file %s is more recent than source, skipping" % self.target, "Rules/Build")

    # {{{2 Install
    def _installAction(self):
        if not self.options.has_key("def_install") or self.options['def_install'] in ('', 'def_install'):
            log.debug("Applying def_install to %s." % self.file, "Rules/Install")
            cfg = config.getConfig()
            root = cfg.getRoot()
            src = os.path.join(root, 'dst', self.file)
            return actions.def_install(src)
        else:
            act = self.options['def_install']
            if 'std_' + act in dir(actions):
                log.debug("Applying non-default install method %s to %s." % (act, self.file), "Rules/Install")
                return eval('actions.std_' + act)
            else:
                log.debug("Calling %s for installing %s to %s" % (act, self.file, self.target), "Rules/Install")
                return actions.call_cmd(act)

    def install(self):
        cfg = config.getConfig()
        root = cfg.getRoot()
        install_root = cfg.getInstallRoot()
        src = os.path.join(root, 'dst', self.file)
        dst = os.path.join(install_root, self.target)
        src_time = getTime(src)
        act = self._installAction()
        self._preinstall(src, dst)
        if not os.path.exists(dst):
            log.notice("Target for %s doesn't exist yet." % src, "Rules/Install")
            act(src, dst)
        else:
            dst_time = getTime(dst)
            if src_time < dst_time:
                log.warn("Target %s has changed more recently than %s." % (dst, src), "Rules/Install")
            act(src, dst)
        self._postinstall(src, dst)

    # {{{3 pre/post install actions
    def _preinstall(self, src, dst):
        if not self.options.has_key('preinstall') or self.options['preinstall'] == '':
            return
        cmd = self.options['preinstall']
        actions.custom_preinstall(src, dst, cmd)

    def _postinstall(self, src, dst):
        if not self.options.has_key('postinstall') or self.options['preinstall'] == '':
            return
        cmd = self.options['postinstall']
        actions.custom_postinstall(src, dst, cmd)

    # {{{2 retrieve
    def _retrieveAction(self):
        if not self.options.has_key("def_retrieve") or self.options['def_retrieve'] in ('', 'def_retrieve'):
            log.debug("Applying def_retrieve to %s." % self.file, "Rules/Retrieve")
            cfg = config.getConfig()
            install_root = cfg.getInstallRoot()
            installed = os.path.join(install_root, self.target)
            root = cfg.getRoot()
            src = os.path.join(root, 'src', self.file)
            dst = os.path.join(root, 'dst', self.file)
            return actions.def_retrieve(installed, src, dst)
        else:
            act = self.options['def_retrieve']
            if 'std_' + act in dir(actions):
                log.debug("Applying non-default retrieve method %s to %s." % (act, self.file), "Rules/Retrieve")
                return eval('actions.std_' + act)
            else:
                log.debug("Calling %s for retrieveing %s to %s" % (act, self.file, self.target), "Rules/Retrieve")
                return actions.call_cmd(act)

    def retrieve(self):
        cfg = config.getConfig()
        root = cfg.getRoot()
        install_root = cfg.getInstallRoot()
        installed = os.path.join(install_root, self.target)
        src = os.path.join(root, 'dst', self.file)
        act = self._retrieveAction()
        if not os.path.exists(src):
            log.warn("Trying to retrieve %s, not available in repo !!" % installed, "Rules/Retrieve")
            act(installed, src)
        elif not os.path.exists(installed):
            log.crit("Unable to retrieve non-existing file %s" % installed, "Rules/Retrieve")
        else:
            act(installed, src)

    # {{{2 backport
    def _backportAction(self):
        if not self.options.has_key("def_backport") or self.options['def_backport'] in ('', 'def_backport'):
            log.debug("Applying def_backport to %s." % self.file, "Rules/Backport")
            cfg = config.getConfig()
            root = cfg.getRoot()
            dst = os.path.join(root, 'dst', self.file)
            src = os.path.join(root, 'src', self.file)
            return actions.def_backport(dst, src)
        else:
            act = self.options['def_backport']
            if 'std_' + act in dir(actions):
                log.debug("Applying non-default backport method %s to %s." % (act, self.file), "Rules/Backport")
                return eval('actions.std_' + act)
            else:
                log.debug("Calling %s for backporting %s to %s" % (act, self.file, self.target), "Rules/Backport")
                return actions.call_cmd(act)

    def backport(self):
        cfg = config.getConfig()
        root = cfg.getRoot()
        src = os.path.join(root, 'src', self.file)
        dst = os.path.join(root, 'dst', self.file)
        act = self._backportAction()
        if not os.path.exists(src):
            log.warn("Trying to backport to %s, which doesn't exist !" % src, "Rules/Backport")
            act(dst, src)
        elif not os.path.exists(dst):
            log.crit("Unable to backport non-existing file %s" % dst, "Rules/Backport")
        else:
            time_src = getTime(src)
            time_dst = getTime(dst)
            if time_src > time_dst:
                log.warn("Warning : backporting %s onto %s which changed more recently" % (dst, src), "Rules/Backport")
            act(dst, src)

    # {{{2 diff
    def _diffAction(self):
        if not self.options.has_key("def_diff") or self.options['def_diff'] in ('', 'def_diff'):
            log.debug("Applying def_diff to %s." % self.file, "Rules/Diff")
            return actions.def_diff()
        else:
            act = self.options['def_diff']
            if 'std_' + act in dir(actions):
                log.debug("Applying non-default diff method %s to %s." % (act, self.file), "Rules/Diff")
                return eval('actions.std_' + act)
            else:
                log.debug("Calling %s for diffing %s with %s" % (act, self.file, self.target), "Rules/Diff")
                return actions.call_cmd(act)

    def diff(self):
        cfg = config.getConfig()
        root = cfg.getRoot()
        install_root = cfg.getInstallRoot()
        src = os.path.join(root, 'dst', self.file)
        dst = os.path.join(install_root, self.target)
        if not os.path.exists(src):
            log.warn("Trying to find diffs for %s, which doesn't exist !" % self.file, "Rules/Diff")
        elif not os.path.exists(dst):
            log.warn("Installed file %s doesn't exist !" % dst, "Rules/Diff")
        act = self._diffAction()
        act(src, dst)

    # {{{2 check
    def _checkAction(self):
        """Returns the action for checking : generally def_check"""
        if not self.options.has_key("def_check") or self.options['def_check'] in ('', 'def_check'):
            log.debug("Applying def_check to %s." % self.file, "Rules/Check")
            return actions.def_check()
        else:
            act = self.options['def_check']
            if 'std_' + act in dir(actions):
                log.debug("Applying non-default check method %s to %s." % (act, self.file), "Rules/Check")
                return eval('actions.std_' + act)
            else:
                log.debug("Calling %s for checking %s with %s" % (act, self.file, self.target), "Rules/Check")
                return actions.call_cmd(act)

    def check(self):
        cfg = config.getConfig()
        root = cfg.getRoot()
        install_root = cfg.getInstallRoot()
        src = os.path.join(root, 'src', self.file)
        dst = os.path.join(root, 'dst', self.file)
        installed = os.path.join(install_root, self.target)
        if not os.path.exists(src):
            log.warn("Source file %s is missing !!" % src, "Rules/Check")
        if not os.path.exists(dst):
            log.warn("Compiled file %s is missing !!" % dst, "Rules/Check")
        if not os.path.exists(installed):
            log.warn("Installed file %s is missing !!" % installed, "Rules/Check")
        act = self._checkAction()
        act(src, dst, installed)



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

    log.debug("Parsing %s" % pre, "RuleParser")

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
class CplxApplier:
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
        log.debug("Rule is %s" % (" ".join(tokens)), "RuleParser")
        res = eval(" ".join(tokens))
        self.__cur_cats = set()
        return res

