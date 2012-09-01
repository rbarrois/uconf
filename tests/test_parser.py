# coding: utf-8
# Copyright (c) 2010-2012 Raphaël Barrois

import unittest

from confmgr import parser

class RuleLexerTestCase(unittest.TestCase):

    def setUp(self):
        self.rule_lexer = parser.RuleLexer()

    def test_simple(self):
        rules = (
            ('a', parser._TextNode('a')),
            ('a && b', parser._AndNode(
                [parser._TextNode('a'), parser._TextNode('b')])),
            ('a || b', parser._OrNode(
                [parser._TextNode('a'), parser._TextNode('b')])),
            ('!a', parser._NegateNode(parser._TextNode('a'))),
            ('a || (b || c)', parser._OrNode([
                parser._TextNode('a'),
                parser._TextNode('b'),
                parser._TextNode('c'),
                ])),
            ('a && !b', parser._AndNode([
                parser._TextNode('a'),
                parser._NegateNode(parser._TextNode('b')),
                ])),
        )

        for rule_text, expected_node in rules:
            rule = self.rule_lexer.get_rule(rule_text)
            self.assertEqual(expected_node, rule.node)


if __name__ == '__main__':
    unittest.main()
