#!/usr/bin/python
# -*- coding: utf-8 -*-

import ConfigParser, os, re, subprocess

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
        re_section = re.compile("^\[([a-zA-Z0-9]+)\][ \t]*$")
        re_spl_row = re.compile("^\s*(\S+)\s*[=:]\s*(\S+)\s*$")
        re_cplx_row = re.compile("^([\S \t]+)[ \t]*[=:][ \t]*([\S \t]+)$")
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

class CatRule:
    """Holds a 'category' rule"""

    re_spl_pre = re.compile("^[\w \t]+$")
    def __init__(self, pre, post):
        """Parses a pre and post pair to build the rule"""
        self.simple = False
        if CatRule.re_spl_pre.match(pre) != None:
            self.simple = True
            self.spl_parents = pre.split()
            self.spl_sons = post.split()

    def apply(self, cats):
        if self.simple:
            for cat in self.spl_parents:
                if cat in cats:
                    return set(self.spl_sons)
            return set([])
        else:
            return set([])

class FileRule:
    re_spl_pre = re.compile("^[\w \t]+$")
    def __init__(self, pre, post):
        self.simple = False
        self.sons = post.split()
        if re_spl_pre.match(pre) != None:
            self.simple = True
            self.spl_parents = pre.split()

    def apply(self, cats):
        if self.simple:
            for cat in self.spl_parents:
                if cat in cats:
                    return set(self.sons)
            return set([])
        else:
            return set([])
