#!/usr/bin/python
# -*- coding: utf-8 -*-

# Global imports
import os, re

# Local imports
import log, config, actions

# {{{1 def getTime()
def getTime(file):
    cfg = config.getConfig()
    return os.path.getmtime(os.path.join(cfg.getRoot(), file))


# {{{1 class FileRule
class FileRule:
    def __init__(self, file, target, options = ''):
        self.file = file
        self.target = target
        self.parseOptions(options)
        log.debug("Added rule for '%s' : target is '%s', with options %s" % (file, target, options))

    def parseOptions(self, options):
        self.options = options.split(',')

    def build(self):
        cfg = config.getConfig()
        # TODO : check 'config' timestamp as well
        root = cfg.getRoot()
        src = os.path.join(root, 'src', self.file)
        dst = os.path.join(root, 'dst', self.file)
        src_time = getTime(src)
        if not os.path.exists(dst):
            log.notice("Target for %s doesn't exist yet." % self.file)
            actions.std_build(src, dst)
        else:
            dst_time = getTime(dst)
            if dst_time < src_time:
                log.notice("Source file %s has changed, updating %s" % (self.file, self.target))
            actions.std_build(src, dst)

    def install(self):
        cfg = config.getConfig()
        root = cfg.getRoot()
        install_root = cfg.get("DEFAULT", "install_root")
        src = os.path.join(root, 'dst', self.file)
        dst = os.path.join(os.path.expanduser(install_root), self.target)
        src_time = getTime(src)
        if not os.path.exists(dst):
            log.notice("Target for %s doesn't exist yet." % src)
            actions.std_install(src, dst)
        else:
            dst_time = getTime(dst)
            if src_time < dst_time:
                log.warn("Target %s has changed more recently than %s !!!" % (dst, src))
            actions.std_install(src, dst)

    def retrieve(self):
        cfg = config.getConfig()
        root = cfg.getRoot()
        install_root = cfg.get("DEFAULT", "install_root")
        installed = os.path.join(os.path.expanduser(install_root), self.target)
        src = os.path.join(root, 'dst', self.file)
        if not os.path.exists(src):
            log.warn("Trying to retrieve %s, not available in repo !!" % installed)
            actions.std_retrieve(installed, src)
        elif not os.path.exists(installed):
            log.crit("Unable to retrieve non-existing file %s" % installed)
        else:
            actions.std_retrieve(installed, src)

    def backport(self):
        cfg = config.getConfig()
        root = cfg.getRoot()
        src = os.path.join(root, 'src', self.file)
        dst = os.path.join(root, 'dst', self.file)
        if not os.path.exists(src):
            log.warn("Trying to backport to %s, which doesn't exist !" % src)
            actions.std_copy(dst, src)
        elif not os.path.exists(dst):
            log.crit("Unable to backport non-existing file %s" % dst)
        else:
            time_src = getTime(src)
            time_dst = getTime(dst)
            if time_src > time_dst:
                log.warn("Warning : backporting %s onto %s which changed more recently" % (dst, src))
            actions.std_backport(src, dst)



# {{{1 def filenameSplit(txt, amount)
def filenameSplit(txt, amount = 0):
    """Splits a text into at most amount filenames strings

    if amount is 0 (default), the string will be split into every non-empty filename encountered.

    '\\ ' is converted to a space, '\\\\' to '\\'
    '\\x' with x neither ' ' nor '\\' is simply removed."""
    parts = []
    prev_is_backslash = False
    cur = ""
    for x in txt:
        if x == '\\':
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
                cur += ' '
            prev_is_backslash = False
        elif x == '\t':
            prev_is_backslash = False
            if amount == 0 or len(parts) < amount - 1:
                if cur != "":
                    parts.append(cur)
                    cur = ""
            else:
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

    log.debug("Parsing %s" % pre)

    split_re = '[ \t]*([()!]|and|or|not|&&|\|\|)[ \t]*'
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
        log.debug("Rule is %s" % (" ".join(tokens)))
        res = eval(" ".join(tokens))
        self.__cur_cats = set()
        return res

