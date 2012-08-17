# coding: utf-8
# Copyright (c) 2010-2012 Raphaël Barrois

import unittest

from confmgr import parser

class RuleLexerTestCase(unittest.TestCase):

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

        for rule, expected_node in rules:
            node = parser.parse_rule(rule)
            self.assertEqual(expected_node, node)


if __name__ == '__main__':
    unittest.main()
