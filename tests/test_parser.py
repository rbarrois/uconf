#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2010-2013 Raphaël Barrois
# This software is distributed under the two-clause BSD license.

import re
import unittest

from uconf import action_parser
from uconf import rule_parser

class RuleLexerTestCase(unittest.TestCase):

    def setUp(self):
        self.rule_lexer = rule_parser.RuleLexer()

    def test_simple(self):
        rules = (
            ('a', rule_parser._TextNode('a')),
            ('a && b', rule_parser._AndNode(
                [rule_parser._TextNode('a'), rule_parser._TextNode('b')])),
            ('a || b', rule_parser._OrNode(
                [rule_parser._TextNode('a'), rule_parser._TextNode('b')])),
            ('!a', rule_parser._NegateNode(rule_parser._TextNode('a'))),
            ('a || (b || c)', rule_parser._OrNode([
                rule_parser._TextNode('a'),
                rule_parser._TextNode('b'),
                rule_parser._TextNode('c'),
                ])),
            ('a && !b', rule_parser._AndNode([
                rule_parser._TextNode('a'),
                rule_parser._NegateNode(rule_parser._TextNode('b')),
                ])),
        )

        for rule_text, expected_node in rules:
            rule = self.rule_lexer.get_rule(rule_text)
            self.assertEqual(expected_node, rule.node)


class ActionLexerTestCase(unittest.TestCase):
    def setUp(self):
        self.action_lexer = action_parser.ActionLexer()

    def test_single_quoted_regexps(self):
        samples = (
            (r"'foo'", r"'foo'"),
            (r"'foo\"bar'", r"'foo\"bar'"),
            (r"'foo\bar'", r"'foo\bar'"),
            (r"'foo\'bar'", r"'foo\'bar'"),
            (r"'foo'bar'", r"'foo'"),
            (r"'foo\\'bar'", r"'foo\\'"),
        )

        regexp = re.compile(action_parser.SingleQuotedTextToken.regexp)

        for source, target in samples:
            m = regexp.match(source)
            self.assertIsNotNone(m, "No match found in %r" % source)
            self.assertEqual(m.group(), target)

    def test_double_quoted_regexps(self):
        samples = (
            (r'"foo"', r'"foo"'),
            (r'"foo\'bar"', r'"foo\'bar"'),
            (r'"foo\bar"', r'"foo\bar"'),
            (r'"foo\"bar"', r'"foo\"bar"'),
            (r'"foo"bar"', r'"foo"'),
            (r'"foo\\"bar"', r'"foo\\"'),
        )

        regexp = re.compile(action_parser.DoubleQuotedTextToken.regexp)

        for source, target in samples:
            m = regexp.match(source)
            self.assertIsNotNone(m, "No match found in %r" % source)
            self.assertEqual(m.group(), target)

    def test_simple(self):
        samples = (
            (r'foo', {'foo': None}),
            (r'foo bar', {'foo': None, 'bar': None}),
            (r' foo', {'foo': None}),
            (r'  foo   ', {'foo': None}),
            (r'foo   bar', {'foo': None, 'bar': None}),
            (r'foo=bar bar', {'foo': 'bar', 'bar': None}),
            (r'foo=bar bar=foo foo=bar', {'foo': 'bar', 'bar': 'foo'}),
            (r'foo="bar"', {'foo': 'bar'}),
            (r'foo=" bar "', {'foo': ' bar '}),
            (r"foo='bar'", {'foo': 'bar'}),
            (r"foo=' bar '", {'foo': ' bar '}),
            (r'foo="bar\"baz"', {'foo': 'bar"baz'}),
            (r"""foo="bar\"baz" bar='baz\'foo'""",
                {'foo': 'bar"baz', 'bar': 'baz\'foo'}),
        )

        for text, expected in samples:
            options = self.action_lexer.get_options(text)
            self.assertEqual(options, expected)


if __name__ == '__main__':
    unittest.main()
