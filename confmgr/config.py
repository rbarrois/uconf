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

# {{{1 class Config
class Config:
    """Purpose : store all config"""

    # {{{2 __init__
    def __init__(self):
        self.config = ConfigParser.SafeConfigParser(self.getDefaults())
        self.config.read([systemConfig, os.path.expanduser(userConfig)])
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
        """Returns a dict of default values"""
        # Put all default config here
        data = dict()
        data['root'] = os.path.expanduser("~/conf")
        return data

    # {{{2 findRoot, setRoot
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

    # {{{2 readRepoConfig
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
                            elif section.lower() in ("files", "file"):
                                self.__files.append((pre.strip(), post.strip()))

    # {{{2 finalize
    def finalize(self):
        if self.finalized:
            return
        self.finalized = True
        if len(self.__cats) == 0 and len(self.__files) == 0:
            self.readRepoConfig()
        self.__loadCats()
        self.__loadFiles()
        self.__loadRules()

    # {{{2 __loadCats
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
            rules.append(CatExpandRule(pre, post))
        for rule in rules:
            self.cats = self.cats | rule.apply(self.cats)

    # {{{2 __loadFiles
    def __loadFiles(self):
        """Prepare list of files to build"""
        if len(self.cats) == 0:
            self.__loadCats()
        rules = []
        for (pre, post) in self.__files:
            rules.append(FileExpandRule(pre, post))
        for rule in rules:
            self.files = self.files | rule.apply(self.cats)

    # {{{2 __loadRules
    def __loadRules(self):
        """Load the list of rules, file per file"""
        if len(self.files) == 0:
            log.debug("No files to handle.")
            return

        root = self.get("DEFAULT", "root")
        path_files = []
        fnd = subprocess.Popen(["find", root, "-type", "f", "-a", "-name", "__paths"], stdout = subprocess.PIPE).communicate()[0]
        for row in fnd.split():
            path_files.append(row)
        path_files.sort()
        log.debug("Path_files are : " + ", ".join(path_files))

        for path_file in path_files:
            self.mergePathFile(path_file)

    # {{{3 mergePathFile
    def mergePathFile(self, path_file):
        commands = []

        re_file_init = re.compile('^[^ \t]')
        re_ignore_row = re.compile('^[ \t]*#')
        re_keep_going_row = re.compile(r'[^\\]\\$')
        cur = ""
        keep_reading = False
        with open(path_file) as f:
            for line in f:
                row = line[:-1]
                if re_ignore_row.match(row) == None:
                    if keep_reading:
                        cur += row
                    else:
                        if re_file_init.match(row) != None:
                            if cur != "":
                                commands.append(cur)
                            cur = row
                        else:
                            log.warn("Erroneous row %s in %s." % (row, path_file))
                    if re_keep_going_row.match(row) != None:
                        # Strip the '\' at the end of cur
                        cur = cur[:-1]
                        keep_reading = True
                    else:
                        keep_reading = False
        if cur != "":
            commands.append(cur)

        for command in commands:
            parts = filenameSplit(command, 3)
            if len(parts) < 2:
                log.warn("Too short line : %s" % command)
                continue
            file = parts[0]
            target = parts[1]
            options = ''
            if len(parts) == 3:
                options = parts[2]
            self.filerules[file] = FileRule(file, target, options)

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
        cfg = getConfig()
        print "o< o< o< %s >o >o >o" % self.file

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

# {{{1 class CplxApplier
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

# {{{1 class CatExpandRule
class CatExpandRule:
    """Holds a 'category' rule"""

    re_spl_pre = re.compile("^[\w \t]+$")
    def __init__(self, pre, post):
        """Parses a pre and post pair to build the rule"""
        self.simple = False
        self.sons = set(post.split())
        if CatExpandRule.re_spl_pre.match(pre) != None:
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

# {{{1 class FileExpandRule
class FileExpandRule:
    re_spl_pre = re.compile("^[\w \t]+$")

    def __init__(self, pre, post):
        self.simple = False
        self.sons = set(post.split())
        if FileExpandRule.re_spl_pre.match(pre) != None:
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
