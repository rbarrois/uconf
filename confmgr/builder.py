#!/usr/bin/python
# -*- coding: utf-8 -*-

import os

import core

class Builder(core.ActionModule):
    def call(self, command, args):
        if command == "build":
            self.build(args)
        print("Calling %s -- %s" % (command, repr(args)))
        print("Root is %s" % self.config.get("DEFAULT", "root"))

    def build(self, args):
        print repr(self.config.cats)
        files = core.getFiles()
        print repr(files)
        print "o<"
