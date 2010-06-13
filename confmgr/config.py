#!/usr/bin/env python2.6
# -*- coding: utf-8 -*-

# Global imports
import ConfigParser, os, re, subprocess

# Local imports
import log, misc


systemConfig = "/etc/confmgr.conf"
userConfig = "~/.confmgr"

def getConfig():
    conf = cfg
    if conf is None:
        log.fulldebug("Initializing config.", module="Config")
        conf = Config()
    return conf

# {{{1 class Config
class Config(object):
    """Purpose : store all config"""

    # {{{2 __init__
    def __init__(self):
        # get defaults
        self.config = self.getDefaults()
        self.config.read([systemConfig, os.path.expanduser(userConfig)])
        # initialize data
        self.cats = set([])
        self.files = set([])
        self.__cats = []
        self.__files = []
        self.filerules = dict()
        self.finalized = False

    # {{{2 get, getDefaults
    def get(self, section, var):
        return self.config.get(section, var)

    def getDefaults(self):
        """Returns a SafeConfigParser of default values"""
        # Put all default config here
        default = dict()
        default['root'] = os.path.expanduser("~/conf")
        default['srcdir'] = 'src'
        default['dstdir'] = 'dst'
        data = ConfigParser.SafeConfigParser(default)
        data.add_section('rules')
        data.set('rules', 'preinstall', "")
        data.set('rules', 'postinstall', "")
        data.set('rules', 'def_build', "")
        data.set('rules', 'def_install', "")
        return data

    # {{{2 findRoot, setRoot
    def findRoot(self):
        """Finds the root of the current repo"""
        path = os.getcwd()
        confRoot = self.getRoot()
        # Check whether we are already in the default config dir
        if os.path.relpath(path, confRoot)[:2] != "..":
            log.debug("Already within default root", "Config/FindRoot")
            return confRoot

        while path != "":
            if os.path.isdir(path):
                if "config" in os.listdir(path):
                    log.debug("Found repo root at %s" % path, "Config/FindRoot")
                    return path
                else:
                    path = os.path.dirname(path)
            else:
                log.crit("Incorrect path : %s is not a dir" % path, "Config/FindRoot")
                exit(1)
        log.crit("Unable to find repo root", "Config")
        exit(1)

    def setRoot(self, root):
        """Stores the path of the root of the current repo (if it exists)"""
        if os.path.exists(root):
            self.config.set("DEFAULT", "root", root)
        else:
            log.crit("Can't set repo root to non existent path %s" % root, "Config")
            exit(1)
        if os.path.exists(root + "/config") and os.access(root + "/config", os.R_OK):
            self.readRepoConfig(root + "/config")

    # {{{2 Access to paths (getRoot, getInstallRoot, getSrc, getDst)
    def getRoot(self):
        return os.path.expanduser(self.config.get("DEFAULT", "root"))

    def getInstallRoot(self):
        return os.path.expanduser(self.config.get("DEFAULT", "install_root"))

    def getSrc(self):
        return os.path.join(self.getRoot(), self.config.get("DEFAULT", "srcdir"))

    def getSrcSubdir(self):
        return self.config.get("DEFAULT", 'srcdir')

    def getDst(self):
        return os.path.join(self.getRoot(), self.config.get("DEFAULT", "dstdir"))

    def getDstSubdir(self):
        return self.config.get("DEFAULT", 'dstdir')

    # {{{2 Setters
    def setHost(self, hostname):
        self.config.set("DEFAULT", 'hostname', hostname)
        self.__reload()

    def setDst(self, dstdir):
        self.config.set("DEFAULT", 'dstdir', dstdir)

    # {{{2 readRepoConfig
    def readRepoConfig(self, configfile = None):
        if configfile is None:
            configfile = self.getRoot() + "/config"

        log.debug("Reading repo config from %s" % configfile, module="Config")
        section = "DEFAULT"

        # Matches a section header
        re_section = re.compile("^\[(\w+)\][ \t]*$")

        # Matches a config row : a = X
        re_cfg_row = re.compile("^[ \t]*(\w+)[ \t]*[=:][ \t]*([^ ].*)$")

        # Matches a cat / file row : (a && b || ! b) and (a or not b) = c d
        re_cplx_row = re.compile("^[ \t]*([\w!()&| \t]+)[ \t]*[=:][ \t]*([\S \t]+)$")
        with open(configfile) as f:
            for line in f:
                row = line[:-1]
                m = re_section.match(row)
                if m is not None:
                    section = m.group(1)
                else:
                    if section.upper() == "DEFAULT":
                        m = re_cfg_row.match(row)
                        if m is not None:
                            (key, val) = m.groups()
                            self.config.set("DEFAULT", key, val)
                    else:
                        m = re_cplx_row.match(row)
                        if m is not None:
                            (pre, post) = m.groups()
                            if section.lower() in ("categories", "cats", "category"):
                                self.__cats.append((pre.strip(), post.strip()))
                            elif section.lower() in ("files", "file"):
                                self.__files.append((pre.strip(), post.strip()))

    # {{{2 getRulesOptions
    def getRulesOptions(self):
        """Returns a dict of options read from config files"""
        self.finalize()
        options = self.config.items("rules")
        opts = dict()
        for (key, val) in options:
            opts[key] = val
        return opts

    # {{{2 mergeCLIOptions
    def mergeCLIOptions(self, options):
        """Returns options once cli values have been merged into it"""
        return options

    # {{{2 getActionsOptions
    def getActionsOptions(self, actionname):
        """Returns options for a given action"""
        return dict()

    # {{{2 finalize
    def finalize(self):
        if self.finalized:
            return
        self.finalized = True
        if len(self.__cats) == 0 and len(self.__files) == 0:
            self.readRepoConfig()
        self.__reload()

    # {{{2 __reload
    def __reload(self):
        self.__loadCats()
        self.__loadFiles()
        self.__loadRules()

    # {{{2 __loadCats
    def __loadCats(self):
        """Parse category rules and apply them"""

        # Read default cats
        if self.config.has_option("DEFAULT", "cats"):
            self.cats = set(self.config.get("DEFAULT", "cats").split())
        else:
            self.cats = set()
        if self.config.has_option("DEFAULT", "hostname"):
            hostname = self.config.get("DEFAULT", "hostname")
        else:
            hostname = subprocess.Popen(["hostname", "-s"], stdout=subprocess.PIPE).communicate()[0][:-1]
        self.cats = self.cats | set([hostname])

        # Read rules and apply them
        rules = []
        for (pre, post) in self.__cats:
            rules.append(CatExpandRule(pre, post))
        for rule in rules:
            self.cats = self.cats | rule.apply(self.cats)
        log.notice("Active categories are " + ", ".join(self.cats), "Config/loadCats")

    # {{{2 __loadFiles
    def __loadFiles(self):
        """Prepare list of files to build"""
        if len(self.cats) == 0:
            self.__loadCats()
        rules = []
        self.files = set()
        for (pre, post) in self.__files:
            rules.append(FileExpandRule(pre, post))
        for rule in rules:
            self.files = self.files | rule.apply(self.cats)

    # {{{2 __loadRules
    def __loadRules(self):
        """Load the list of rules, file per file"""
        if len(self.files) == 0:
            log.debug("No files to handle.", module="Config/loadRules")
            return

        root = self.getRoot()
        path_files = []
        fnd = subprocess.Popen(["find", root, "-type", "f", "-a", "-name", "__paths"], stdout = subprocess.PIPE).communicate()[0]
        for row in fnd.split():
            path_files.append(row)
        path_files.sort()
        log.debug("Path_files are : " + ", ".join(path_files), module="Config/loadRules")

        for path_file in path_files:
            self.mergePathFile(path_file)

    # {{{3 mergePathFile
    def mergePathFile(self, path_file):
        r"""Reads __path files ; all \x sequences IN FILE NAMES will be
        translated ; nothing will be done to those in options."""
        commands = []

        subdir = os.path.relpath(
                os.path.dirname(path_file),
                os.path.join(self.getRoot(), 'src'))

        re_file_init = re.compile('^[^ \t]')
        re_ignore_row = re.compile('^[ \t]*#')
        re_keep_going_row = re.compile(r'[^\\]\\$')
        cur = ""
        keep_reading = False
        with open(path_file) as f:
            for line in f:
                row = line[:-1]
                if re_ignore_row.match(row) is None:
                    if keep_reading:
                        cur += row
                    else:
                        if re_file_init.match(row) is not None:
                            if cur != "":
                                commands.append(cur)
                            cur = row
                        else:
                            log.warn("Erroneous row %s in %s." % (row, path_file), "Config/PathFiles")
                    if re_keep_going_row.match(row) is not None:
                        # Strip the '\' at the end of cur
                        cur = cur[:-1]
                        keep_reading = True
                    else:
                        keep_reading = False
        if cur != "":
            commands.append(cur)

        for command in commands:
            parts = misc.filenameSplit(command, 3)
            if len(parts) < 2:
                log.warn("Too short line : %s" % command, "Config/PathFiles")
                continue
            filename = os.path.join(subdir, parts[0])
            target = parts[1]
            options = ''
            if len(parts) == 3:
                options = parts[2]
            self.filerules[filename] = misc.FileRule(filename, target, options)

# {{{1 class CatExpandRule
class CatExpandRule(object):
    """Holds a 'category' rule"""

    re_spl_pre = re.compile("^[\w \t]+$")
    def __init__(self, pre, post):
        """Parses a pre and post pair to build the rule"""
        self.simple = False
        self.sons = set(post.split())
        if CatExpandRule.re_spl_pre.match(pre) is not None:
            self.simple = True
            self.spl_parents = pre.split()
        else:
            self.rule = misc.parse_cplx_pre(pre)

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

# {{{1 class FileExpandRule
class FileExpandRule(object):
    re_spl_pre = re.compile("^[\w \t]+$")

    def __init__(self, pre, post):
        self.simple = False
        self.sons = set(post.split())
        if FileExpandRule.re_spl_pre.match(pre) is not None:
            self.simple = True
            self.spl_parents = pre.split()
        else:
            self.rule = misc.parse_cplx_pre(pre)

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

# {{{1 Initiate cfg
if 'cfg' not in dir():
    log.fulldebug("cfg not created yet, initializing.", "Config")
    cfg = Config()

