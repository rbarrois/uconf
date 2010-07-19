#!/usr/bin/env python2.6
# -*- coding: utf-8 -*-

from __future__ import with_statement

# Global imports
import os
import re
import difflib
import hashlib
import subprocess
import distutils.file_util as f_util

# Local imports
import log
import config
import misc


def isTextFile(file):
    """Determines, through 'file -b FILE', whether FILE is text"""
    filetype = subprocess.Popen(['file', '-b', file], stdout=subprocess.PIPE).communicate()[0]
    return ('text' in [x.strip(' ,.') for x in filetype.split()])

def getHash(strings):
    """Returns the md5 hash of the strings row array"""
    _hash = hashlib.md5()
    for row in strings:
        _hash.update(row)
    return _hash.hexdigest()

def linkTarget(file):
    if not os.path.islink(file):
        return None
    else:
        return os.path.join(os.path.dirname(file), os.readlink(file))

# {{{1 File parsing
# {{{2 get_output(src)
def get_output(src):
    """Wrapper around parse_file, outputs only lines to be printed"""
    for (do_print, line, raw) in parse_file(src):
        if do_print:
            yield line

# {{{2 parse_file(src)
def parse_file(src):
    """Generator for the list of rows obtained from the file src"""
    cfg = config.getConfig()
    cats = cfg.cats

    re_command = re.compile('^["!#]@[^@#]')
    re_comment = re.compile('^["!#]@#')
    re_escaped = re.compile('^["!#]@@')

    in_block = False
    write = True
    for line in src:
        if line[-1:] == "\n":
            row = line[:-1]
        else:
            row = line
        if re_comment.match(row) is not None:
            log.debug("Encountered comment : {0}".format(row), "FileParser")
            yield (False, '', line)
        elif write and re_escaped.match(row) is not None:
            log.debug("Escaping row : {0}".format(row), "FileParser")
            yield (True, row[:2] + row[3:] + "\n", line)
        elif re_command.match(row) is not None:
            parts = row[2:].split(' ', 1)
            command = parts[0]
            log.debug("Encountered command {0}".format(command), "FileParser")
            if command == "end" and in_block:
                write = True
                in_block = False
            elif command == "if":
                in_block = True
                rule = misc.parse_cplx_pre(parts[1])
                if rule.apply(cats):
                    write = True
                    log.debug("Rule {0} has matched.".format(parts[1]), "FileParser")
                else:
                    write = False
                    log.debug("Rule {0} didn't match.".format(parts[1]), "FileParser")
            elif in_block and command == "else":
                write = not write
                log.debug("Switching writing to {0}".format(write), "FileParser")
            yield(False, '', line)
        elif write:
            yield (True, line, line)
        else:
            yield (False, '', line)

# {{{2 revert(line)
def revert(line):
    """Returns the raw line which did generate line"""
    if len(line) > 1 and line[0] in ('!', '#', '"') and line[1] == "@":
        return line[0] + "@" + line[1:]
    else:
        return line

# {{{1 Default commands
# Default commands are called from FileRule ; they select which std_command should be returned

# {{{2 def_build
def def_build(file):
    """Determines the correct action for building file :

    - build (for text files)
    - copy (for binaries)
    - copy_link (for symlinks)"""

    if os.path.islink(file):
        return stdCopyLinkAction()
    else:
        if isTextFile(file):
            return stdBuildAction()
        else:
            return stdCopyAction()

# {{{2 def_install
def def_install(file):
    """Determines the correct action for installing file :

    - copy (for normal files)
    - copy_link (for symlinks)"""

    if os.path.islink(file):
        return stdCopyLinkAction()
    else:
        return stdInstallAction()

# {{{2 def_retrieve
def def_retrieve(file, src, dst):
    """Determines the correct action for retrieving file :

    - retrieve (for normal files)
    - copy_link (for symlinks)
    - none if file is already a link to src or dst"""

    if os.path.islink(file):
        tgt = linkTarget(file)
        if tgt in (dst, src):
            return stdEmptyAction()
        else:
            return stdCopyLinkAction()
    else:
        return stdRetrieveAction()

# {{{2 def_backport
def def_backport(file, src):
    """Determines the correct action for retrieving file :

    - backport (for normal files)
    - copy (for binary files)
    - copy_link (for symlinks)"""

    if os.path.islink(file):
        tgt = linkTarget(file)
        if tgt == src:
            return stdEmptyAction()
        else:
            return stdCopyLinkAction()
    else:
        if isTextFile(file):
            return stdBackportAction()
        else:
            return stdCopyAction()

# {{{2 def_diff
def def_diff():
    """Determines the correct action for diffing two files : always 'diff' :p"""
    return stdDiffAction()

# {{{2 def_check
def def_check():
    """Determines the correct action for checking a file : always std_check :p"""
    return stdCheckAction()

# {{{1 standard commands

# {{{2 Model of actions
class ActionResult(object):
    """Stores the result of an action, as a couple (success, msg) (msg being a list of str)"""
    def __init__(self, success = False, msg = None):
        self.success = success
        self.msg = msg

class Action(object):
    """Stores an action.

    This is an abstract class, all subclasses must implement their "apply" method.
    A given action should be applicable to a whole set of files ; custom parameters can be passed as second argument to "apply"
    @param defaults Additional options to those from config
    """

    def __init__(self, defaults = None):
        self.defaults = dict()
        cfg = config.getConfig()
        for (key, val) in cfg.getActionsOptions(self.__class__.__name__).items():
            self.defaults[key] = val
        if defaults is not None:
            for (key, val) in defaults.getItems():
                self.defaults[key] = val

    def _default(self, key, defval = None):
        """Retrieves values from self.defaults

        @param key The name of the property being retrieved
        @param defval The default value to return if self.defaults[key] isn't defined
        @return either self.defaults[key], or defval
        """
        if not key in self.defaults:
            return defval
        else:
            return self.defaults[key]

    def apply(self, src, dst, *params):
        """Applys the given action to a file
        @param src is the filename to use as input
        @param dst is the filename to use as output
        @param params Other parameters
        A rule should NEVER alter src.

        The parent calling function will already have called log.info(..., with_success = True);
        the function can add a comment (log.comment(...,). log.success() will be called
        according to the return value.
        """
        return ActionResult(success = False, msg = "You called an empty 'apply' method")

    def batchApply(self, batch):
        """Applies the action to a batch of files
        This file is a list of tuples (name, src, dst, param1, param2, ...)
        It will return a dict of name => ActionResult of the action
        """
        res = dict()
        for rule in batch:
            if len(rule) != 0 and len(rule) < 3:
                res[rule[0]] = ActionResult(msg = "Empty rule ?!?")
            else:
                res[rule[0]] = self.apply(rule[1], rule[2], *rule[3:])
        return res

# {{{2 stdBuildAction
class stdBuildAction(Action):
    """Default building of a file"""

    def apply(self, src, dst, *params):
        log.comment("Building {src} to {dst}".format(src = src, dst = dst))
        with open(dst, 'w') as g:
            with open(src, 'r') as f:
                for line in get_output(f):
                    g.write(line)
        return ActionResult(success = True)

# {{{2 stdBackportAction
class stdBackportAction(Action):
    """Default backporting of a file to another one

    Its action is :
        1. 'build' dst in memory
        2. Find the diffs between that build version and src
        3. Convert those diffs into diffs in the raw file
        4. Apply those diffs to dst
    """

    def apply(self, src, dst, *params):
        # Load compiled versions
        with open(dst, 'r') as f:
            orig = [line for line in get_output(f)]
        with open(src, 'r') as f:
            modified = [line for line in f]
        # Check whether they differ
        md5_orig = getHash(orig)
        md5_dest = getHash(modified)
        if md5_orig == md5_dest:
            return ActionResult(success = True, msg = "Skipped (md5 hash of compiled and source are the same).")

        # Compute the diff
        newdst = []
        diff = difflib.ndiff(orig, modified)

        # For each line in the raw file, look at the diff and adapt :
        #   if diff is + X, add X ; if diff is - X, don't print ; else, print
        #   and continue to next line
        with open(dst, 'r') as f:
            for (do_print, txt, raw) in parse_file(f):
                if do_print:
                    dif = diff.next()
                    log.fulldebug(dif, 'Backport')
                    while dif[0] in ('+', '?'):
                        if dif[0] == '+':
                            newdst.append(revert(dif[2:]))
                        dif = diff.next()
                        log.fulldebug(dif, 'Backport')
                    if dif[0] == '-':
                        continue
                    else:
                        newdst.append(raw)
                else:
                    newdst.append(raw)
        for dif in diff:
            if dif[0] == '+':
                newdst.append(dif[2:])
        with open(dst, 'w') as f:
            [f.write(line) for line in newdst]

        return ActionResult(success = True)

# {{{2 stdInstallAction
class stdInstallAction(Action):
    """Default installation of a file"""

    def apply(self, src, dst, *params):
        log.comment("Installing {src} on {dst}".format(src = src, dst = dst))
        dst_dir = os.path.dirname(dst)
        if not os.path.exists(dst_dir):
            dst_dir = os.path.dirname(dst)
            log.comment("Folder {0} doesn't exist, creating".format(dst_dir))
            os.makedirs(dst_dir)
        (dstname, copied) = f_util.copy_file(src, dst, preserve_mode = True, preserve_times = True, update = True)
        if copied:
            return ActionResult(success = True)
        else:
            return ActionResult(success = False)

# {{{2 stdCopyAction
class stdCopyAction(Action):
    """Default copy of a file (like install, but no checks)"""

    def apply(self, src, dst, *params):
        f_util.copy_file(src, dst, preserve_mode = False, preserve_times = True, update = False)
        return ActionResult(success = True)

# {{{2 stdCopyLinkAction
class stdCopyLinkAction(Action):
    """Copies a link (i.e if a->b is copied to c->b)"""

    def apply(self, src, dst, *params):
        log.comment("Replicating symlink {src} to {dst}".format(src = src, dst = dst))
        tgt = os.readlink(src)
        if os.path.exists(dst):
            os.unlink(dst)
        os.symlink(tgt, dst)
        return ActionResult(success = True)

# {{{2 stdRetrieveAction
class stdRetrieveAction(Action):
    """Retrieves an installed file"""

    def apply(self, src, dst, *params):
        log.debug("Retrieving {dst} from {src}".format(src = src, dst = dst))
        dst_dir = os.path.dirname(dst)
        if not os.path.exists(dst_dir):
            dst_dir = os.path.dirname(dst)
            log.comment("Folder {0} doesn't exist, creating".format(dst_dir))
            os.makedirs(dst_dir)
        f_util.copy_file(src, dst, update = False)
        return ActionResult(success = True)

# {{{2 stdLinkAction
class stdLinkAction(Action):
    """Links dst to src"""

    def apply(self, src, dst, *params):
        log.comment("Linking {dst} to {src}".format(src = src, dst = dst))
        os.symlink(src, dst)
        return ActionResult(True)

# {{{2 stdEmptyAction
class stdEmptyAction(Action):
    """Does nothing"""

    def apply(self, src, dst, *params):
        return ActionResult(True, "Nothing done for {src} to {dst}".format(src = src, dst = dst))

# {{{2 stdDiffAction
class stdDiffAction(Action):
    """Computes the raw diff between src and dst"""

    def apply(self, src, dst, *params):
        diff = subprocess.Popen(["diff", "-Nur", src, dst], stdout=subprocess.PIPE).communicate()[0]
        if len(diff) > 0:
            log.display("vimdiff {src} {dst}".format(src = src, dst = dst))
            [log.display(row) for row in diff.splitlines()]
        return ActionResult(success = len(diff) == 0)

# {{{2 stdCheckAction
class stdCheckAction(Action):
    """Verifies that all goes fine between src, dst, installed"""

    def apply(self, src, dst, *params):
        if len(params) < 1:
            log.crit("Error in the code: not enough parameters")
            return ActionResult(success = False)
        installed = params[0]
        # Load compiled versions
        with open(src, 'r') as f:
            orig = [line for line in get_output(f)]
        if not os.path.exists(dst):
            return ActionResult(success = False, msg = "File {0} hasn't be compiled, please run 'build'".format(dst))

        with open(dst, 'r') as f:
            dest = [line for line in f]

        same = True
        msgs = []
        # Check whether they differ
        md5_orig = getHash(orig)
        md5_dest = getHash(dest)
        if md5_orig != md5_dest:
            msgs.append("Found diff between {src} and compiled version {dst}.".format(src = src, dst = dst))
            same = False

        log.fulldebug("Calling diff {dst} {prod}".format(dst = dst, prod = installed), "Actions/Check")
        DEVNULL = open('/dev/null', 'w')
        retcode = subprocess.call(["diff", dst, installed], stdout = DEVNULL, stderr = DEVNULL)
        if retcode != 0:
            msgs.append("Found diff between {dst} and installed version {prod}.".format(dst = dst, prod = installed))
            same = False
        if same:
            return ActionResult(success = True)
        else:
            return ActionResult(success = False, msg = '; '.join(msgs))

# {{{1 custom command callers
# {{{2 callCmdAction
class callCmdAction(Action):
    def __init__(self, cmd):
        self.cmd = cmd

    def apply(self, src, dst, *params):
        res = subprocess.call(self.cmd + [src, dst] + [arg for arg in params])
        return ActionResult(success = (res == 0))

# {{{2 customPreinstallAction
class customPreinstallAction(Action):
    """Calls cmd (and explains it happened before dst installation)"""

    def __init__(self, cmd):
        self.cmd = cmd

    def apply(self, src, dst, *params):
        log.info("Pre-install ({dst}) : running {cmd}".format(dst = dst, cmd = self.cmd), with_success = True)
        ret = subprocess.call(self.cmd)
        if ret != 0:
            log.warn("Error : pre-install action for {dst} exited with code {ret}".format(dst = dst, ret = ret), "Actions/custom_preinstall")
            log.fail()
        else:
            log.success()

# {{{2 customPostinstallAction
class customPostinstallAction(Action):
    """Calls cmd (and explains it happened after dst installation)"""
    def __init__(self, cmd):
        self.cmd = cmd

    def apply(self, src, dst, *params):
        log.info("Post-install ({dst}) : running {cmd}".format(dst = dst, cmd = self.cmd), with_success = True)
        ret = subprocess.call(self.cmd)
        if ret != 0:
            log.warn("Error : post-install action for {dst} exited with code {ret}".format(dst = dst, ret = ret), "Actions/custom_postinstall")
            log.fail()
        else:
            log.success()

# {{{1 Build list of available actions
__actionsdir = dir()

def getActionsList():
    acts = dict()
    for x in __actionsdir:
        if len(x) > 6 and x[-6:] == 'Action':
            acts[x.lower()] = x
    return acts

def actionExists(act):
    return act in all

def actionName(act):
    if actionExists(act):
        return all[act.lower()]

all = getActionsList()
