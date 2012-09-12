# coding: utf-8
# Copyright (c) 2010-2012 Raphaël Barrois

import unittest

from confmgr import rule_parser

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


if __name__ == '__main__':
    unittest.main()
