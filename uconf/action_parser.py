# -*- coding: utf-8 -*-
# Copyright (c) 2010-2013 Raphaël Barrois
# This software is distributed under the two-clause BSD license.

"""Handles parsing of action options."""

import collections
import re
import tdparser


Option = collections.namedtuple('Option', ('key', 'value'))


class IdentifierToken(tdparser.Token):
    """An option."""
    lbp = 20
    regexp = r'[a-z0-9_-]+'

    def __init__(self, text):
        self.text = text

    def nud(self, context):
        """Try to retrieve the value."""
        return [Option(self.text, None)]


class EqualToken(tdparser.Token):
    """The equal sign, between an identifier and a token."""
    lbp = 30
    regexp = r'='

    def led(self, left, context):
        identifier, value = left[0]

        if value is not None:
            raise ValueError("Invalid chained '%s=%s=%s'." % (
                identifier, value, context.consume().text))

        if isinstance(context.current_token, IdentifierToken):
            # The lexer mistook our value for an identifier, let's take it.
            value = context.consume().text
        else:
            # That's a "standard" value, let's pick it.
            value = context.expression(self.lbp)

        return [Option(identifier, value)]


class SpaceToken(tdparser.Token):
    """A space (separates options).

    Lower binding power so that id=value gets glued together.
    """
    lbp = 10
    regexp = r' +'

    def nud(self, context):
        # At the beginning of the string
        return context.expression(self.lbp)

    def led(self, left, context):
        """Simply sum expressions on the left and on the right."""
        return left + context.expression(self.lbp)


class BaseValueToken(tdparser.Token):
    """Any valid value."""
    lbp = 20

    def clean_text(self):
        return self.text

    def nud(self, context):
        return self.clean_text()


class UnQuotedTextToken(BaseValueToken):
    regexp = r"[^'\" ]+"


class BaseQuotedTextToken(BaseValueToken):

    def clean_text(self):
        text = self.text[1:-1]
        # Strip a level of backslashes
        text = re.sub(r'\\(.)', r'\1', text)
        return text


class DoubleQuotedTextToken(BaseQuotedTextToken):
    regexp = r'"([^\\"]|\\.)*"'


class SingleQuotedTextToken(BaseQuotedTextToken):
    regexp = r"'([^\\']|\\.)*'"


class ActionLexer:
    def __init__(self, lexer=None):
        self.lexer = lexer or self._build_lexer()

    @classmethod
    def _build_lexer(cls):
        lexer = tdparser.Lexer(with_parens=False, blank_chars='')
        lexer.register_tokens(IdentifierToken, EqualToken, DoubleQuotedTextToken, SingleQuotedTextToken, SpaceToken)
        return lexer

    def get_options(self, text):
        options = self.lexer.parse(text.strip())
        return dict(options)
