#!/usr/bin/python
# -*- coding: utf-8 -*-

class ActionModule:
    def __init__(self, config):
        self.config = config

    def getHelp(self, command):
        print(self.__doc__)

    def _call(self, command, args):
        """Wrapper for call (print help if requested)"""
        if len(args) > 0 and ("-h" in args or "--help" in args):
            self.getHelp(command)
        else:
            self.call(command, args)

    def call(self, command, args):
        """Stub for real action in modules"""
        pass

def getFiles():
    return []
