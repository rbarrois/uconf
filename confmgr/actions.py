#!/usr/bin/python
# -*- coding: utf-8 -*-

# Global imports
import os, re, difflib, md5
import distutils.file_util as f_util

# Local imports
import log, config, misc

def get_output(src):
    """Wrapper around parse_file, outputs only lines to be printed"""
    for (do_print, line, raw) in parse_file(src):
        if do_print:
            yield line

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
            log.debug("Encountered comment : %s" % row)
            yield (False, '', line)
        elif write and re_escaped.match(row) != None:
            log.debug("Escaping row : %s" % row)
            yield (True, row[:2] + row[3:] + "\n", line)
        elif re_command.match(row) != None:
            parts = row[2:].split(' ', 2)
            command = parts[0]
            log.debug("Encountered command %s" % command)
            if command == "end" and in_block:
                write = True
                in_block = False
            elif command == "if":
                in_block = True
                rule = misc.parse_cplx_pre(parts[1])
                if rule.apply(cats):
                    write = True
                    log.debug("Rule %s has matched." % parts[1])
                else:
                    write = False
                    log.debug("Rule %s didn't match." % parts[1])
            elif in_block and command == "else":
                write = not write
                log.debug("Switching writing to %s" % write)
            yield(False, '', line)
        elif write:
            yield (True, line, line)
        else:
            yield (False, '', line)

def std_build(src, dst):
    """Builds (normally) a file"""
    with open(dst, 'w') as g:
        with open(src, 'r') as f:
            for line in get_output(f):
                g.write(line)

def revert(line):
    """Returns the raw line which did generate line"""
    if len(line) > 1 and line[0] in ('!', '#', '"') and line[1] == "@":
        return line[0] + "@" + line[1:]
    else:
        return line

def std_backport(src, dst):
    """Finds differences between dst version and result of the compilation of src, and adapts src as needed"""

    # Load compiled versions
    with open(src, 'r') as f:
        orig = [line for line in get_output(f)]
    with open(dst, 'r') as f:
        dest = [line for line in f]

    # Check whether they differ
    md5_orig = md5.new(''.join(orig)).digest()
    md5_dest = md5.new(''.join(dest)).digest()
    if md5_orig == md5_dest:
        log.info("MD5 hash of %s[compiled] and %s are the same, skipping." % (src, dst))
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
                while dif[0] == '+':
                    newsrc.append(revert(dif[2:]))
                    dif = diff.next()
                if dif[0] == '-':
                    continue
                else:
                    newsrc.append(raw)
            else:
                newsrc.append(raw)
    for dif in diff:
        newsrc.append(dif[2:])
    with open(src, 'w') as f:
        [f.write(line) for line in newsrc]


def std_install(src, dst):
    log.info("Installing %s on %s" % (src, dst))
    f_util.copy_file(src, dst, preserve_mode = True, preserve_times = True, update = True)

def std_copy(src, dst):
    log.info("Copying %s to %s" % (src, dst))
    f_util.copy_file(src, dst, preserve_mode = False, preserve_times = True, update = True)

def std_retrieve(installed, src):
    log.info("Retrieving %s from %s" % (src, installed))
    f_util.copy_file(installed, src, update = True)
