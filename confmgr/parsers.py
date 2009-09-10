#!/usr/bin/python
# -*- coding: utf-8 -*-

# Global imports
import os, re

# Local imports
import log, config, misc


def std_build(src, dst):
    """Builds (normally) a file"""
    cfg = config.getConfig()
    cats = cfg.cats
    root = cfg.getRoot()
    full_src = os.path.join(root, src)
    full_dst = os.path.join(root, dst)

    re_command = re.compile('^["!#]@[^@#]')
    re_comment = re.compile('^["!#]@#')
    re_escaped = re.compile('^["!#]@@')

    in_block = False
    write = True
    with open(full_src) as f:
        with open(full_dst, 'w') as g:
            for line in f:
                row = line[:-1]
                if re_comment.match(row) != None:
                    log.debug("Encountered comment : %s" % row)
                    continue
                elif write and re_escaped.match(row) != None:
                    log.debug("Escaping row : %s" % row)
                    g.write(row[:2] + row[3:] + "\n")
                elif re_command.match(row) != None:
                    parts = row[2:].split(' ', 2)
                    command = parts[0]
                    log.debug("Encountered command %s" % command)
                    if command == "end" and in_block:
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
                elif write:
                    g.write(line)

