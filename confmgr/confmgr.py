#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys, os, optparse, subprocess, shutil

# local imports
import log, config, actions, misc

#version = @@VERSION@@
version = '@VERSION@'

# {{{1 __checkCfg
def __checkCfg(findRoot = True):
    cfg = config.getConfig()
    if not cfg.finalized:
        cfg.finalize()
    if findRoot:
        cfg.findRoot()
    return cfg

modules = ["init", "update", "build", "install", "diff", "check", "retrieve", "backport", "import" ]

def printVersion():
    sys.stdout.write("""Confmgr %s
Copyright (C) 2009 XelNet

Written by Raphaël Barrois (Xelnor).\n""" % version)

def __init_parser(mth):
    parser = optparse.OptionParser(mth.__doc__, add_help_option = False)
    # Verbosity
    parser.set_defaults(verbosity = 0)
    parser.set_defaults(quietness = 0)
    parser.add_option("-h", "--help", action="help", help=optparse.SUPPRESS_HELP)
    parser.add_option("-v", "--verbose", action="count", dest="verbosity", help=optparse.SUPPRESS_HELP)
    parser.add_option("-q", "--quiet", action="count", dest="quietness", help=optparse.SUPPRESS_HELP)
    return parser

def __set_verb(opts):
    log.setLogLevel(log.getLogLevelFromVerbosity(opts.verbosity - opts.quietness))

# {{{1 __getMethods
def __getMethods(dir):
    """Lists methods implemented in current code"""
    res = []
    for item in dir:
        if item[:4] == "cmd_":
            res.append(item)
    return res

# {{{1 __getMethod
def __getMethod(command):
    cmd = "cmd_" + command
    if cmd in __methods:
        return eval(cmd)
    else:
        log.crit("Unknown command %s." % command, "Core")
        exit(1)

# {{{1 getHelp
def getHelp(cmd):
    cmd = __getMethod(cmd).__name__
    doc = eval(cmd + '.__doc__')
    if doc == None:
        return ""
    else:
        return doc

# {{{1 call
def call(command, args):
    """Wrapper to confmgr.command(args)"""
    __checkCfg(False)
    mth = __getMethod(command)
    parser = eval('__parse_' + command)
    opts = None
    arg = None
    if parser != None:
        (opts, args) = parser(args)
    __set_verb(opts)
    return mth(opts, args)

# {{{1 do_import
def do_import(path, folder, cat="All"):
    cfg = config.getConfig()
    repo_root = cfg.getRoot()
    install_root = cfg.getInstallRoot()
    src_path = os.path.join(repo_root, 'src')
    absfolder = os.path.join(src_path, folder)

    if not os.path.exists(absfolder):
        log.notice("Creating the %s folder" % absfolder)
        os.makedirs(absfolder)

    if not os.path.isdir(absfolder):
        log.crit("Unable to create %s, skipping file." % absfolder)

    pathfile = os.path.join(absfolder, '__paths')
    files = []

    abspath = os.path.abspath(path)
    is_folder = (os.path.basename(path) == '' or os.path.isdir(abspath))
    if is_folder:
        # Folder
        log.debug("Importing folder %s" % abspath, module="Import")
        if not os.path.exists(abspath):
            log.warn("Folder %s doesn't exist, skipping." % abspath)
            return
        fnd = subprocess.Popen(["find", abspath, "-type", "f"], stdout = subprocess.PIPE).communicate()[0]
        for row in fnd.split():
            files.append((os.path.relpath(row, abspath), row))
    else:
        # Regular file
        log.debug("Importing file %s" % abspath, module="Import")
        if not os.path.exists(abspath):
            log.warn("File %s doesn't exist, I won't copy it into the 'src' folder." % abspath)
        files = [(os.path.basename(path), abspath)]

    files.sort()
    # Handle files
    with open(pathfile, 'a') as f:
        for (file, install_file) in files:
            relp = os.path.relpath(install_file, install_root)
            log.debug("Adding file %s" % file, module="Import")
            f.write("%s %s\n" % (file, relp))
            if os.path.exists(install_file):
                dirname = os.path.dirname(file)
                absdirname = os.path.join(absfolder, dirname)
                if dirname != '' and dirname != '.' and not os.path.exists(absdirname):
                    os.makedirs(absdirname)
                shutil.copy(install_file, os.path.join(absfolder, file))
    with open(os.path.join(repo_root, "config"), 'a') as g:
        g.write("%s: %s\n" % (cat, ' '.join([os.path.join(folder,file) for (file, install_file) in files])))

def do_init(root, install_root):
    """Initializes a repo in 'root' with the given 'install_root'"""
    hostname = subprocess.Popen(["hostname", "-s"], stdout=subprocess.PIPE).communicate()[0][:-1]
    conf = os.path.join(root, "config")
    skel =
    """[default]
install_root = %s

[cats]
%s = all

[files]
""" % (install_root, hostname)
    with open(conf, 'w') as f:
        f.write(skel)
    os.mkdir(os.path.join(root, 'src'))
    os.mkdir(os.path.join(root, 'dst'))

# {{{1 commands

# {{{2 cmd_init
def __parse_init(args):
    """Parses args and returns (opts, args)"""
    parser = __init_parser(cmd_init)
    parser.add_option("-i", "--install-path", action="store", dest="install_root", default="", help="Path for installed files")
    return parser.parse_args(args)

def cmd_init(opts, args):
    """Initialize a confmgr repo here"""
    cfg = __checkCfg(False)
    cfg.setRoot(os.getcwd())
    do_init(cfg.getRoot(), opts.install_root)

# {{{2 cmd_update
def __parse_update(args):
    """Parses args and returns (opts, args)"""
    parser = __init_parser(cmd_update)
    return parser.parse_args(args)

def cmd_update(opts, args):
    """Update repo (through an update of the VCS)"""
    cfg = __checkCfg()

# {{{2 cmd_import
def __parse_import(args):
    """Parses args and returns (opts, args)"""
    parser = __init_parser(cmd_import)
    parser.add_option("-c", "--category", action="store", dest="cat", default="all", help="Put the files into category CAT")
    parser.add_option("-f", "--folder", action="store", dest="folder", default=None, help="Import files into FOLDER (FOLDER is taken relative to the 'src' folder of the repo)")
    return parser.parse_args(args)

def cmd_import(opts, args):
    """Import a folder into the repo"""
    cfg = __checkCfg()

    if opts.folder == None:
        log.crit("Error : The 'folder' argument is mandatory.")
        sys.exit(1)
    repo_root = cfg.getRoot()
    src_path = os.path.join(repo_root, 'src')
    folder = os.path.normpath(opts.folder)

    if not misc.isSubdir(folder, os.path.join(repo_root, 'src')):
        log.crit("Error : the target folder must be within the 'src' folder of repo (given : %s)" % folder)
        sys.exit(1)
    folder = os.path.relpath(os.path.join(src_path, folder), src_path)
    log.info("Adding files to the %s folder (%s)" % (folder, os.path.join(src_path, folder)))

    cat = opts.cat
    for file in args:
        do_import(file, folder=folder, cat=cat)

# {{{2 cmd_build
def __parse_build(args):
    """Parses args and returns (opts, args)"""
    parser = __init_parser(cmd_build)
    return parser.parse_args(args)

def cmd_build(opts, files):
    """Build all files needed for this host

    No options.
    Optionnally, a list of files to build can be given when calling."""
    cfg = __checkCfg()
    known_files = cfg.filerules.keys()

    # Load files given as arguments
    _files = []
    if len(files) > 0:
        for file in files:
            if file not in cfg.files:
                log.warn("No configuration for file %s, ignoring." % file)
            else:
                _files.append(file)
    else:
        _files = cfg.files

    for file in _files:
        if file not in known_files:
            log.warn("No rules given for file %s, ignoring." % file)
        else:
            rule = cfg.filerules[file]
            rule.build()

# {{{2 cmd_install
def __parse_install(args):
    """Parses args and returns (opts, args)"""
    parser = __init_parser(cmd_install)
    parser.add_option("-f", "--force", action="store_true", dest="force", help="Force install")
    return parser.parse_args(args)

def cmd_install(opts, args):
    """Install all built files to their targets"""
    cfg = __checkCfg()
    known_files = cfg.filerules.keys()
    for file in cfg.files:
        if file not in known_files:
            log.warn("No rules given for file %s, ignoring." % file)
        else:
            rule = cfg.filerules[file]
            rule.install()

# {{{2 cmd_check
def __parse_check(args):
    """Parses args and returns (opts, args)"""
    parser = __init_parser(cmd_check)
    return parser.parse_args(args)

def cmd_check(opts, args):
    """Outputs list of files where there are diffs :
    - Between source and compiled
    - Between compiled and installed"""
    cfg = __checkCfg()
    known_files = cfg.filerules.keys()
    for file in cfg.files:
        if file not in known_files:
            log.warn("No rules given for file %s, ignoring." % file)
        else:
            rule = cfg.filerules[file]
            rule.check()

# {{{2 cmd_retrieve
def __parse_retrieve(args):
    """Parses args and returns (opts, args)"""
    parser = __init_parser(cmd_retrieve)
    return parser.parse_args(args)

def cmd_retrieve(opts, args):
    """Retrive installed files"""
    cfg = __checkCfg()
    known_files = cfg.filerules.keys()
    for file in cfg.files:
        if file not in known_files:
            log.warn("No rules given for file %s, ignoring." % file)
        else:
            rule = cfg.filerules[file]
            rule.retrieve()

# {{{2 cmd_backport
def __parse_backport(args):
    """Parses args and returns (opts, args)"""
    parser = __init_parser(cmd_backport)
    return parser.parse_args(args)

def cmd_backport(opts, args):
    """Backport modifications of retrieved files to their source versions"""
    cfg = __checkCfg()
    known_files = cfg.filerules.keys()
    for file in cfg.files:
        if file not in known_files:
            log.warn("No rules given for file %s, ignoring." % file)
        else:
            rule = cfg.filerules[file]
            rule.backport()

# {{{2 cmd_diff
def __parse_diff(args):
    """Parses args and returns (opts, args)"""
    parser = __init_parser(cmd_diff)
    return parser.parse_args(args)

def cmd_diff(opts, args):
    """Print diff between compiled files and installed versions."""
    cfg = __checkCfg()
    known_files = cfg.filerules.keys()
    for file in cfg.files:
        if file not in known_files:
            log.warn("No rules given for file %s, ignoring." % file)
        else:
            rule = cfg.filerules[file]
            rule.diff()

__methods = __getMethods(dir())
