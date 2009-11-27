#!/usr/bin/python
# -*- coding: utf-8 -*-

# Global imports
import os, re, difflib, hashlib, subprocess
import distutils.file_util as f_util

# Local imports
import log, config, misc

def isTextFile(file):
    """Determines, through 'file -b FILE', whether FILE is text"""
    type = subprocess.Popen(['file', '-b', file], stdout=subprocess.PIPE).communicate()[0]
    return ('text' in [x.strip(' ,.') for x in type.split()])

def getHash(strings):
    """Returns the md5 hash of the strings row array"""
    hash = hashlib.md5()
    for row in strings:
        hash.update(row)
    return hash.hexdigest()

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
        if re_comment.match(row) != None:
            log.debug("Encountered comment : %s" % row, "FileParser")
            yield (False, '', line)
        elif write and re_escaped.match(row) != None:
            log.debug("Escaping row : %s" % row, "FileParser")
            yield (True, row[:2] + row[3:] + "\n", line)
        elif re_command.match(row) != None:
            parts = row[2:].split(' ', 2)
            command = parts[0]
            log.debug("Encountered command %s" % command, "FileParser")
            if command == "end" and in_block:
                write = True
                in_block = False
            elif command == "if":
                in_block = True
                rule = misc.parse_cplx_pre(parts[1])
                if rule.apply(cats):
                    write = True
                    log.debug("Rule %s has matched." % parts[1], "FileParser")
                else:
                    write = False
                    log.debug("Rule %s didn't match." % parts[1], "FileParser")
            elif in_block and command == "else":
                write = not write
                log.debug("Switching writing to %s" % write, "FileParser")
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
        return std_copy_link
    else:
        if isTextFile(file):
            return std_build
        else:
            return std_copy

# {{{2 def_install
def def_install(file):
    """Determines the correct action for installing file :

    - copy (for normal files)
    - copy_link (for symlinks)"""

    if os.path.islink(file):
        return std_copy_link
    else:
        return std_install

# {{{2 def_retrieve
def def_retrieve(file, src, dst):
    """Determines the correct action for retrieving file :

    - retrieve (for normal files)
    - copy_link (for symlinks)
    - none if file is already a link to src or dst"""

    if os.path.islink(file):
        tgt = linkTarget(file)
        if tgt in (dst, src):
            return std_none
        else:
            return std_copy_link
    else:
        return std_retrieve

# {{{2 def_backport
def def_backport(file, src):
    """Determines the correct action for retrieving file :

    - backport (for normal files)
    - copy (for binary files)
    - copy_link (for symlinks)"""

    if os.path.islink(file):
        tgt = linkTarget(file)
        if tgt == src:
            return std_none
        else:
            return std_copy_link
    else:
        if isTextFile(file):
            return std_backport
        else:
            return std_copy

# {{{2 def_diff
def def_diff():
    """Determines the correct action for diffing two files : always 'diff' :p"""
    return std_diff

# {{{2 def_check
def def_check():
    """Determines the correct action for checking a file : always std_check :p"""
    return std_check

# {{{1 standard commands
# {{{2 std_build
def std_build(src, dst):
    """Builds (normally) a file"""
    log.info("Building %s to %s" % (src, dst), with_success = True)
    with open(dst, 'w') as g:
        with open(src, 'r') as f:
            for line in get_output(f):
                g.write(line)
    log.success()

# {{{2 std_backport
def std_backport(dst, src):
    """Finds differences between dst version and result of the compilation of src, and adapts src as needed"""

    # Load compiled versions
    with open(src, 'r') as f:
        orig = [line for line in get_output(f)]
    with open(dst, 'r') as f:
        dest = [line for line in f]

    # Check whether they differ
    md5_orig = getHash(orig)
    md5_dest = getHash(dest)
    if md5_orig == md5_dest:
        log.info("Skipping %s (md5 hash of compiled and source are the same)." % src)
        return

    # Compute the diff
    newsrc = []
    diff = difflib.ndiff(orig, dest)

    # For each line in the raw file, look at the diff and adapt :
    #   if diff is + X, add X ; if diff is - X, don't print ; else, print
    #   and continue to next line
    with open(src, 'r') as f:
        for (do_print, txt, raw) in parse_file(f):
            if do_print:
                dif = diff.next()
                log.fulldebug(dif)
                while dif[0] == '+':
                    newsrc.append(revert(dif[2:]))
                    dif = diff.next()
                if dif[0] == '-' or dif[0] == '?':
                    continue
                else:
                    newsrc.append(raw)
            else:
                newsrc.append(raw)
    for dif in diff:
        newsrc.append(dif[2:])
    with open(src, 'w') as f:
        [f.write(line) for line in newsrc]

# {{{2 std_install
def std_install(src, dst):
    log.info("Installing %s on %s" % (src, dst), with_success = True)
    if not os.path.exists(os.path.dirname(dst)):
        dir = os.path.dirname(dst)
        log.notice("Folder %s doesn't exist, creating" % dir)
        os.makedirs(dir)
    (dstname, copied) = f_util.copy_file(src, dst, preserve_mode = True, preserve_times = True, update = True)
    if copied:
        log.success()
    else:
        log.fail()

# {{{2 std_copy
def std_copy(src, dst):
    log.info("Copying %s to %s" % (src, dst), with_success = True)
    f_util.copy_file(src, dst, preserve_mode = False, preserve_times = True, update = False)
    log.success()

# {{{2 std_copy_link
def std_copy_link(src, dst):
    log.info("Replicating symlink %s to %s" % (src, dst), with_success = True)
    tgt = os.readlink(src)
    if os.path.exists(dst):
        os.unlink(dst)
    os.symlink(tgt, dst)
    log.success()

# {{{2 std_retrieve
def std_retrieve(installed, src):
    log.info("Retrieving %s from %s" % (src, installed), with_success = True)
    if not os.path.exists(os.path.dirname(src)):
        dir = os.path.dirname(src)
        log.notice("Folder %s doesn't exist, creating" % dir)
        os.makedirs(dir)
    f_util.copy_file(installed, src, update = False)
    log.success()

# {{{2 std_link
def std_link(ln_name, target):
    log.info("Linking %s to %s" % (ln_name, target), with_success = True)
    os.symlink(target, ln_name)
    log.success()

# {{{2 std_none
def std_none(src, target):
    log.info("Doing nothing for %s to %s" % (src, target))

# {{{2 std_diff
def std_diff(src, dst):
    diff = subprocess.Popen(["diff", "-Nur", src, dst], stdout=subprocess.PIPE).communicate()[0]
    if len(diff) > 0:
        log.display("vimdiff %s %s" % (src, dst))
        [log.display(row) for row in diff.splitlines()]
    else:
        log.info("No changes for %s" % src)

# {{{2 std_check
def std_check(src, dst, installed):
    # Load compiled versions
    with open(src, 'r') as f:
        orig = [line for line in get_output(f)]
    if not os.path.exists(dst):
        log.display("File %s hasn't be compiled, please run 'build'" % dst)
        return

    with open(dst, 'r') as f:
        dest = [line for line in f]

    same = True
    # Check whether they differ
    md5_orig = getHash(orig)
    md5_dest = getHash(dest)
    if md5_orig != md5_dest:
        log.display("Found diff between %s and compiled version %s." % (src, dst))
        same = False

    log.fulldebug("Calling diff %s %s" % (dst, installed), "Actions/Check")
    DEVNULL = open('/dev/null', 'w')
    retcode = subprocess.call(["diff", dst, installed], stdout = DEVNULL, stderr = DEVNULL)
    if retcode != 0:
        log.display("Found diff between %s and installed version %s." % (dst, installed))
        same = False
    if same:
        log.display("%s is up to date." % installed)

# {{{1 custom command callers
# {{{2 call_cmd(cmd)
def call_cmd(cmd):
    """Returns a function f(x, y, z, ...) => subprocess.call(cmd + [x, y, z, ...])"""
    fn = lambda *args : subprocess.call(cmd + [arg for arg in args])
    return fn

# {{{2 custom_preinstall
def custom_preinstall(src, dst, cmd):
    """Calls cmd (and explains it happened before dst installation)"""
    log.info("Pre-install (%s) : running %s" % (dst, cmd), with_success = True)
    ret = subprocess.call(cmd)
    if ret != 0:
        log.warn("Error : pre-install action for %s exited with code %i" % (dst, ret), "Actions/custom_preinstall")
        log.fail()
    else:
        log.success()

# {{{2 custom_postinstall
def custom_postinstall(src, dst, cmd):
    """Calls cmd (and explains it happened after dst installation)"""
    log.info("Post-install (%s) : running %s" % (dst, cmd), with_success = True)
    ret = subprocess.call(cmd)
    if ret != 0:
        log.warn("Error : post-install action for %s exited with code %i" % (dst, ret), "Actions/custom_postinstall")
        log.fail()
    else:
        log.success()
