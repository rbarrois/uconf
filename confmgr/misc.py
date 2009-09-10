#!/usr/bin/python
# -*- coding: utf-8 -*-

# Global imports
import os, re

# Local imports
import log, config, parsers

# {{{1 def getTime()
def getTime(file):
    cfg = config.getConfig()
    return os.path.getmtime(os.path.join(cfg.getRoot(), file))


# {{{1 class FileRule
class FileRule:
    def __init__(self, file, target, options = ''):
        self.file = os.path.join('src', file)
        self.target = os.path.join('dst', file)
        self.parseOptions(options)
        log.debug("Added rule for '%s' : target is '%s', with options %s" % (file, target, options))

    def parseOptions(self, options):
        self.options = options.split(',')

    def build(self):
        # parsers is imported later, otherwise we have cyclic dependancies
        import parsers
        cfg = config.getConfig()
        # TODO : check 'config' timestamp as well
        root = cfg.getRoot()
        src_time = getTime(self.file)
        if not os.path.exists(os.path.join(root, self.target)):
            log.notice("Target for %s doesn't exist yet." % self.file)
            parsers.std_build(self.file, self.target)
        else:
            dst_time = getTime(self.target)
            if dst_time < src_time:
                log.notice("Source file %s has changed, updating %s" % (self.file, self.target))
            parsers.std_build(self.file, self.target)
        print "o< o< o< %s >o >o >o" % self.file

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

