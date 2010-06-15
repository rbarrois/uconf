#!/usr/bin/env python2.6
# -*- coding: utf-8 -*-

import sys, os, optparse, subprocess, shutil

# local imports
import log, config, misc

#version = @@VERSION@@
version = '@VERSION@'

def printVersion():
    sys.stdout.write("""Confmgr {v}
Copyright (C) 2009 XelNet

Written by Raphaël Barrois (Xelnor).\n""".format(v = version))

# {{{1 __getMethods
def __loadCommands(dir):
    """Lists commands implemented in current code"""
    res = dict()
    for item in dir:
        if item[:3] == "cmd":
            cmd = item[3:].lower()
            res[cmd] = eval(item)
    log.fulldebug("Available commands are : {0}".format(repr(res)), "Core")
    return res

# {{{1 __getCommand
def __getCommand(command):
    if command in __commands:
        return __commands[command]
    else:
        log.crit("Unknown command {0}.".format(command), "Core")
        exit(1)

# {{{1 getHelp
def getHelp(cmd):
    """Returns the docstring of the command cmd"""
    cmd = __getCommand(cmd)
    doc = cmd.getHelp()
    if doc is None:
        return ""
    else:
        return doc

# {{{1 call
def call(command, args):
    """Wrapper to confmgr.command(args)"""
    Command._getCfg(False)
    cmdclass = __getCommand(command)
    log.fulldebug("Found command {0}".format(cmdclass.__name__), "Caller")
    cmd = cmdclass()
    cmd.loadArgs(args)
    return cmd.apply()

# {{{1 commands

# {{{2 Command (Base class for commands)
class Command(object):
    """The class for a given command"""
    # Put the doc for the command in its doc string

    def __init__(self):
        self.opts = None
        self.args = None

    def loadArgs(self, args):
        (self.opts, self.args) = self.__class__.__parse(args)

    @staticmethod
    def _getCfg(findRoot = True):
        """Loads the config, trying to find the correct repo root"""
        cfg = config.getConfig()
        if findRoot:
            cfg.setRoot(cfg.findRoot())
            if not cfg.finalized:
                cfg.finalize()
        return cfg

    @classmethod
    def getHelp(cls):
        """Method used to return help message

        Can be overriden in subclasses"""
        return cls.__doc__

    @classmethod
    def __init_parser(cls):
        """Prepare the options parser for current class
        Should not be overriden in subclasses, use _add_options to add options"""
        parser = optparse.OptionParser(cls.getHelp(), add_help_option = False)
        # Verbosity
        parser.set_defaults(verbosity = 0)
        parser.set_defaults(quietness = 0)
        parser.add_option("-h", "--help", action="help", help=optparse.SUPPRESS_HELP)
        parser.add_option("-v", "--verbose", action="count", dest="verbosity", help=optparse.SUPPRESS_HELP)
        parser.add_option("-q", "--quiet", action="count", dest="quietness", help=optparse.SUPPRESS_HELP)
        return parser

    @classmethod
    def _add_options(cls, parser):
        """Method to use in subclasses for adding options to the parser
        (already loaded with default help and verbosity options)"""
        return

    @classmethod
    def __parse(cls, args):
        """Prepare the parser, and load options from args"""
        parser = cls.__init_parser()
        cls._add_options(parser)
        (opts, args) = parser.parse_args(args)
        log.setLogLevel(log.getLogLevelFromVerbosity(opts.verbosity - opts.quietness))
        return (opts, args)


    def apply(self):
        """Method which should be overriden for each command"""
        pass

    @classmethod
    def applyToFiles(cls, callback, files = None):
        cfg = cls._getCfg()
        if files is None:
            files = cfg.files
        for filename in files:
            if filename not in cfg.filerules:
                log.warn("No rules given for file {0}, ignoring.".format(filename))
            else:
                rule = cfg.filerules[filename]
                callback(rule)

# {{{2 cmdInit
class cmdInit(Command):
    """Initialize a confmgr repo in the current directory"""

    @classmethod
    def _add_options(cls, parser):
        parser.add_option("-i", "--install-path", action="store", dest="install_root", default="", help="Path for installed files")

    def apply(self):
        cfg = self._getCfg(False)
        cfg.setRoot(os.getcwd())
        self.init(cfg.getRoot(), self.opts.install_root)

    @classmethod
    def init(cls, root, install_root, srcdir = None, dstdir = None):
        """Initializes a repo in 'root' with the given 'install_root'"""
        cfg = cls._getCfg(False)
        if srcdir is None:
            srcdir = cfg.getSrcSubdir()
        if dstdir is None:
            dstdir = cfg.getDstSubdir()

        hostname = subprocess.Popen(["hostname", "-s"], stdout=subprocess.PIPE).communicate()[0][:-1]

        conf = os.path.join(root, "config")
        if not os.path.exists(conf):
            skel = """[default]
install_root = {i}

[cats]
{h} = all

[files]

""".format(i = install_root, h = hostname)
            with open(conf, 'w') as f:
                f.write(skel)

        mkdirs = [os.path.join(root, d) for d in [srcdir, dstdir]]
        for mkdir in mkdirs:
            if not os.path.exists(mkdir):
                os.mkdir(mkdir)

# {{{2 cmdUpdate
class cmdUpdate(Command):
    """Update repo (through an update of the VCS)"""

    def apply(self):
        log.display("Not implemented yet.")

# {{{2 cmdImport
class cmdImport(Command):
    """Import a folder into the repo"""

    @classmethod
    def _add_options(cls, parser):
        parser.add_option("-c", "--category", action="store", dest="cat", default="all", help="Put the files into category CAT")
        parser.add_option("-f", "--folder", action="store", dest="folder", default=None, help="Import files into FOLDER (FOLDER is taken relative to the 'src' folder of the repo)")

    def apply(self):
        cfg = self._getCfg()

        if self.opts.folder is None:
            log.crit("Error : The 'folder' argument is mandatory.")
            sys.exit(1)
        src_path = cfg.getSrc()
        folder = os.path.normpath(self.opts.folder)

        if not misc.isSubdir(folder, cfg.getSrc()):
            log.crit("Error : the target folder must be within the '{0}' folder of repo (given : {1})".format(cfg.getSrcSubdir(), folder))
            sys.exit(1)
        folder = os.path.relpath(os.path.join(src_path, folder), src_path)
        log.info("Adding files to the {rel} folder ({abs})".format(rel = folder, abs = os.path.join(src_path, folder)))

        cat = self.opts.cat
        for f in self.args:
            self.importFile(f, folder=folder, cat=cat)

    @classmethod
    def importFile(cls, path, folder, cat="All"):
        cfg = config.getConfig()
        repo_root = cfg.getRoot()
        install_root = cfg.getInstallRoot()
        src_path = cfg.getSrc()
        absfolder = os.path.join(src_path, folder)

        if not os.path.exists(absfolder):
            log.notice("Creating the {0} folder".format(absfolder))
            os.makedirs(absfolder)

        if not os.path.isdir(absfolder):
            log.crit("Unable to create {0}, skipping file.".format(absfolder))

        pathfile = os.path.join(absfolder, '__paths')
        files = []

        abspath = os.path.abspath(path)
        is_folder = (os.path.basename(path) == '' or os.path.isdir(abspath))
        if is_folder:
            # Folder
            log.debug("Importing folder {0}".format(abspath), module="Import")
            if not os.path.exists(abspath):
                log.warn("Folder {0} doesn't exist, skipping.".format(abspath))
                return
            fnd = subprocess.Popen(["find", abspath, "-type", "f"], stdout = subprocess.PIPE).communicate()[0]
            for row in fnd.split():
                files.append((os.path.relpath(row, abspath), row))
        else:
            # Regular file
            log.debug("Importing file {0}".format(abspath), module="Import")
            if not os.path.exists(abspath):
                log.warn("File {0} doesn't exist, I won't copy it into the 'src' folder.".format(abspath))
            files = [(os.path.basename(path), abspath)]

        files.sort()
        # Handle files
        with open(pathfile, 'a') as f:
            for (filename, install_file) in files:
                relp = os.path.relpath(install_file, install_root)
                log.info("Adding file {0}".format(filename), module="Import")
                f.write("{src} {to}\n".format(src = filename, to = relp))
                if os.path.exists(install_file):
                    dirname = os.path.dirname(filename)
                    absdirname = os.path.join(absfolder, dirname)
                    if dirname != '' and dirname != '.' and not os.path.exists(absdirname):
                        os.makedirs(absdirname)
                    shutil.copy(install_file, os.path.join(absfolder, filename))
        with open(os.path.join(repo_root, "config"), 'a') as g:
            g.write("{cat}: {files}\n".format(cat = cat, files = ' '.join([os.path.join(folder,filename) for (filename, install_file) in files])))

# {{{2 cmdExport
class cmdExport(Command):
    """Export the repo for a given host

    The export for host HOST will export into export-HOST a full built tree."""

    @classmethod
    def _add_options(cls, parser):
        parser.add_option("-d", "--dir", action="store", dest="exportdir", default=None, help="Export files into EXPORTDIR")

    def apply(self):
        cfg = self._getCfg()

        if len(self.args) != 1:
            log.crit("Error : you must give the name of exactly one host to export for")
            sys.exit(1)

        target_host = self.args[0]
        exportdir = 'export-' + target_host
        if self.opts.exportdir is not None:
            exportdir = self.opts.exportdir

        cfg.setHost(target_host)
        cfg.setDst(exportdir)
        cmdBuild.build([])

# {{{2 cmdBuild
class cmdBuild(Command):
    """Build all files needed for this host

    No options.
    Optionnally, a list of files to build can be given when calling."""

    def apply(self):
        self.build(self.args)

    @classmethod
    def build(cls, files = []):
        """Actually asks for building all files, or only those given as argument"""
        cfg = cls._getCfg()

        # Load files given as arguments
        _files = []
        if len(files) > 0:
            for filename in files:
                if filename not in cfg.files:
                    # FIXME : unclear code, use os.path.separator ?
                    parts = filename.split('/')
                    if (parts[0] == cfg.getSrcSubdir() or parts[0] == cfg.getDstSubdir()) and '/'.join(parts[1:]) in cfg.files:
                        _files.append('/'.join(parts[1:]))
                    else:
                        log.warn("No configuration for file {0}, ignoring.".format(filename))
                else:
                    _files.append(filename)
        else:
            _files = cfg.files

        cls.applyToFiles(lambda rule: rule.build(), _files)

# {{{2 cmdInstall
class cmdInstall(Command):
    """Install all built files to their targets"""

    @classmethod
    def _add_options(cls, parser):
        parser.add_option("-f", "--force", action="store_true", dest="force", help="Force install")

    def apply(self):
        self.applyToFiles(lambda rule: rule.install())

# {{{2 cmdCheck
class cmdCheck(Command):
    """Outputs list of files where there are diffs

    - Between source and compiled
    - Between compiled and installed"""

    def apply(self):
        self.applyToFiles(lambda rule: rule.check())

# {{{2 cmdRetrieve
class cmdRetrieve(Command):
    """Retrive installed files"""

    def apply(self):
        self.applyToFiles(lambda rule: rule.retrieve())

# {{{2 cmdBackport
class cmdBackport(Command):
    """Backport modifications of retrieved files to their source versions"""

    def apply(self):
        self.applyToFiles(lambda rule: rule.backport())

# {{{2 cmdDiff
class cmdDiff(Command):
    """Print diff between compiled files and installed versions."""

    def apply(self):
        self.applyToFiles(lambda rule: rule.diff())

# {{{1 Global command initialization
__commands = __loadCommands(dir())
modules = __commands.keys()

