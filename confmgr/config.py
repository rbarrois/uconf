#!/usr/bin/python
# -*- coding: utf-8 -*-

# Global imports
import ConfigParser, os, re, subprocess

# Local imports
import log

systemConfig = "/etc/confmgr.conf"
userConfig = "~/.confmgr.conf"

cfg = None

def getConfig():
    conf = cfg
    if conf == None:
        conf = Config()
    return conf

class Config:
    """Purpose : store all config"""


    def __init__(self):
        self.config = ConfigParser.SafeConfigParser(self.getDefaults())
        self.config.read([systemConfig, os.path.expanduser(userConfig)])
        self.cats = set([])
        self.files = set([])
        self.__cats = []
        self.__files = []
        self.finalized = False

    def getDefaults(self):
        """Returns a dict of default values"""
        # Put all default config here
        data = dict()
        data['root'] = os.path.expanduser("~/conf")
        return data

    def findRoot(self):
        """Finds the root of the current repo"""
        path = os.getcwd()
        confRoot = self.config.get("DEFAULT","root")
        # Check whether we are already in the default config dir
        if os.path.relpath(path, confRoot)[:2] is not "..":
            return confRoot

        while path != "":
            if os.path.isdir(path):
                if "config" in os.listdir(path):
                    return path
                else:
                    path = os.path.dirname(path)
            else:
                log.crit("Incorrect path : %s is not a dir" % path)
                exit(1)
        log.crit("Unable to find repo root")
        exit(1)

    def setRoot(self, root):
        """Stores the path of the root of the current repo (if it exists)"""
        if os.path.exists(root):
            self.config.set("DEFAULT", "root", root)
        else:
            log.crit("Can't set repo root to non existent path %s" % root)
            exit(1)
        if os.path.exists(root + "/config") and os.access(root + "/config", os.R_OK):
            self.readRepoConfig(root + "/config")

    def readRepoConfig(self, configfile = None):
        if configfile == None:
            configfile = self.config.get("DEFAULT", "root") + "/config"
        section = "DEFAULT"

        # Matches a section header
        re_section = re.compile("^\[([a-zA-Z0-9]+)\][ \t]*$")

        # Matches a simple row : a b c d = e f g
        re_spl_row = re.compile("^[ \t]*(\w+)[ \t]*[=:][ \t]*(\w+)[ \t]*$")

        # Matches a complex row : (a && b || ! b) and (a or not b) = c d
        re_cplx_row = re.compile("^[ \t]*([\w!()&| \t]+)[ \t]*[=:][ \t]*([\S \t]+)$")
        with open(configfile) as f:
            for line in f:
                row = line[:-1]
                m = re_section.match(row)
                if m != None:
                    section = m.group(1)
                else:
                    if section == "DEFAULT":
                        m = re_spl_row.match(row)
                        if m != None:
                            (key, val) = m.groups()
                            self.config.set("DEFAULT", key, val)
                    else:
                        m = re_cplx_row.match(row)
                        if m != None:
                            (pre, post) = m.groups()
                            if section.lower() in ("categories", "cats", "category"):
                                self.__cats.append((pre.strip(), post.strip()))
                            elif section.lowrt() in ("files", "file"):
                                self.__files.append((pre.strip(), post.strip()))


    def finalize(self):
        if self.finalized:
            return
        self.finalized = True
        if len(self.__cats) == 0 and len(self.__files) == 0:
            self.readRepoConfig()
        self.__loadCats()
        self.__loadFiles()

    def __loadCats(self):
        """Parse category rules and apply them"""

        # Read default cats
        if self.config.has_option("DEFAULT", "cats"):
            self.cats = set(self.config.get("DEFAULT", "cats").split())
        hostname = subprocess.Popen(["hostname", "-s"], stdout=subprocess.PIPE).communicate()[0][:-1]
        self.cats = self.cats | set([hostname])

        # Read rules and apply them
        rules = []
        for (pre, post) in self.__cats:
            rules.append(CatRule(pre, post))
        for rule in rules:
            self.cats = self.cats | rule.apply(self.cats)


    def __loadFiles(self):
        if len(self.cats) == 0:
            self.__loadCats()
        rules = []
        for (pre, post) in self.__files:
            rules.append(FileRule(pre, post))
        for rule in rules:
            self.files = self.files | rule.apply(self.cats)

    def get(self, section, var):
        return self.config.get(section, var)

def parse_cplx_pre(pre):
    """Parses a complex precondition
    and returns a "CplxApplier" object

    expects an expression of the form :
    (a and not b) or (c && ! (d || e))"""

    log.debug("Parsing %s" % pre)

    split_re = '[ \t]*([()!]|and|or|not|&&|\|\|)[ \t]*'
    rawparts = re.split(split_re, pre)
    parts = []
    cats = []
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
        if cln_part not in ("and", "or", "not", "(", ")"):
            cats.append(cln_part)
        parts.append(cln_part)
    return CplxApplier(rule = parts, cats = cats)

class CplxApplier:
    """Holds what is needed to apply a complex rule"""
    def __init__(self, rule, cats):
        self.rule = rule
        self.cats = cats

    def apply(self, cats):
        """Applies the rule to a list of cats"""
        # Load list of enabled cats
        allcats = dict()
        for cat in self.cats:
            allcats[cat] = False
        for cat in cats:
            if cat in self.cats:
                allcats[cat] = True

        # Convert tokens to use allcats[cat] instead of cat
        tokens = []
        for token in self.rule:
            if token not in ("and", "or", "not", "(", ")"):
                tokens.append("allcats['" + token + "']")
            else:
                tokens.append(token)

        # Apply the rule
        log.debug("Rule is %s" % (" ".join(tokens)))
        return eval(" ".join(tokens))

class CatRule:
    """Holds a 'category' rule"""

    re_spl_pre = re.compile("^[\w \t]+$")
    def __init__(self, pre, post):
        """Parses a pre and post pair to build the rule"""
        self.simple = False
        self.sons = set(post.split())
        if CatRule.re_spl_pre.match(pre) != None:
            self.simple = True
            self.spl_parents = pre.split()
        else:
            self.rule = parse_cplx_pre(pre)

    def apply(self, cats):
        if self.simple:
            for cat in self.spl_parents:
                if cat in cats:
                    return self.sons
            return set([])
        else:
            if self.rule.apply(cats):
                return self.sons
            else:
                return set([])

class FileRule:
    re_spl_pre = re.compile("^[\w \t]+$")
    def __init__(self, pre, post):
        self.simple = False
        self.sons = set(post.split())
        if re_spl_pre.match(pre) != None:
            self.simple = True
            self.spl_parents = pre.split()
        else:
            self.rule = parse_cplx_pre(pre)

    def apply(self, cats):
        if self.simple:
            for cat in self.spl_parents:
                if cat in cats:
                    return self.sons
            return set([])
        else:
            if self.rule.apply(cats):
                return self.sons
            else:
                return set([])
