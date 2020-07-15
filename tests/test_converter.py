#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2010-2013 Raphaël Barrois
# This software is distributed under the two-clause BSD license.

import unittest

from uconf import converter


class LineTestCase(unittest.TestCase):
    def test_repr(self):
        self.assertEqual("Line('foo', 'bar')",
            repr(converter.Line('foo', 'bar')))

    def test_equality(self):
        self.assertEqual(
            converter.Line('foo', 'bar'),
            converter.Line('foo', 'bar'))

        self.assertNotEqual(
            converter.Line('foo', 'bar'),
            converter.Line('foo', 'baz'))

        self.assertNotEqual(
            converter.Line('foo', 'bar'),
            converter.Line('fo', 'bar'))

    def test_compare_to_other(self):
        self.assertNotEqual('foo', converter.Line('foo', 'bar'))
        self.assertNotEqual(converter.Line('foo', 'bar'), 'foo')

    def test_hash(self):
        s = set()
        for _i in range(5):
            s.add(converter.Line('foo', 'bar'))

        self.assertEqual(1, len(s))
        self.assertEqual(set([converter.Line('foo', 'bar')]), s)

    def test_fill_original_normal(self):
        l = converter.Line('foo', None)
        self.assertEqual(None, l.original)
        l.fill_original()
        self.assertEqual('foo', l.original)

    def test_fill_original_comment(self):
        l = converter.Line('#@foo', None)
        self.assertEqual(None, l.original)
        l.fill_original()
        self.assertEqual('#@@foo', l.original)

        l = converter.Line('"@foo', None)
        self.assertEqual(None, l.original)
        l.fill_original()
        self.assertEqual('"@@foo', l.original)

        l = converter.Line('!@foo', None)
        self.assertEqual(None, l.original)
        l.fill_original()
        self.assertEqual('!@@foo', l.original)


class BlockStackTestCase(unittest.TestCase):
    def test_bool_value(self):
        s = converter.BlockStack()
        self.assertFalse(s)

        s.enter(converter.Block.KIND_IF, published=True, start_line=1)
        self.assertTrue(s)

    def test_len(self):
        s = converter.BlockStack()
        self.assertEqual(0, len(s))

        s.enter(converter.Block.KIND_IF, published=True, start_line=1)
        self.assertEqual(1, len(s))

    def test_empty_repr(self):
        self.assertEqual("<BlockStack: []>", repr(converter.BlockStack()))

    def test_simple_repr(self):
        s = converter.BlockStack()
        s.enter(converter.Block.KIND_IF, published=True, start_line=1)
        self.assertEqual("<BlockStack: [Block('if', 1, True, {})]>", repr(s))

    def test_empty_published(self):
        s = converter.BlockStack()
        self.assertTrue(s.published)

    def test_simple_published(self):
        s = converter.BlockStack()
        s.enter(converter.Block.KIND_IF, published=True, start_line=1)
        self.assertTrue(s.published)

    def test_simple_unpublished(self):
        s = converter.BlockStack()
        s.enter(converter.Block.KIND_IF, published=False, start_line=1)
        self.assertFalse(s.published)

    def test_stack_published(self):
        s = converter.BlockStack()
        s.enter(converter.Block.KIND_IF, published=True, start_line=1)
        s.enter(converter.Block.KIND_IF, published=True, start_line=2)
        s.enter(converter.Block.KIND_IF, published=True, start_line=3)
        self.assertTrue(s.published)

    def test_stack_unpublished(self):
        s = converter.BlockStack()
        s.enter(converter.Block.KIND_IF, published=True, start_line=1)
        s.enter(converter.Block.KIND_IF, published=False, start_line=2)
        s.enter(converter.Block.KIND_IF, published=True, start_line=3)
        self.assertFalse(s.published)

    def test_stack_unpublished_leave(self):
        s = converter.BlockStack()
        s.enter(converter.Block.KIND_IF, published=True, start_line=1)
        s.enter(converter.Block.KIND_IF, published=True, start_line=2)
        s.enter(converter.Block.KIND_IF, published=False, start_line=3)
        s.enter(converter.Block.KIND_IF, published=True, start_line=4)
        self.assertFalse(s.published)
        s.leave(converter.Block.KIND_IF)
        self.assertFalse(s.published)
        s.leave(converter.Block.KIND_IF)
        self.assertTrue(s.published)

    def test_empty_nolookup(self):
        s = converter.BlockStack()
        self.assertIsNone(s.merged_context.get('foo'))

    def test_simple_keyerror(self):
        s = converter.BlockStack()
        s.enter(converter.Block.KIND_IF, published=True, start_line=1)
        self.assertIsNone(s.merged_context.get('foo'))

    def test_simple_lookup(self):
        s = converter.BlockStack()
        s.enter(converter.Block.KIND_WITH, context={'bar': 'baz'}, start_line=1)
        self.assertIsNone(s.merged_context.get('foo'))
        self.assertEqual('baz', s.merged_context.get('bar'))

    def test_stack_lookup(self):
        s = converter.BlockStack()
        s.enter(converter.Block.KIND_WITH, context={'bar': 1}, start_line=1)
        s.enter(converter.Block.KIND_WITH, context={'baz': 4}, start_line=2)
        s.enter(converter.Block.KIND_WITH, context={'bar': 3}, start_line=3)
        self.assertIsNone(s.merged_context.get('foo'))
        self.assertEqual(4, s.merged_context.get('baz'))
        self.assertEqual(3, s.merged_context.get('bar'))

    def test_stack_lookup_leave(self):
        s = converter.BlockStack()
        s.enter(converter.Block.KIND_WITH, context={'bar': 1}, start_line=1)
        s.enter(converter.Block.KIND_WITH, context={'baz': 4}, start_line=2)
        s.enter(converter.Block.KIND_WITH, context={'bar': 3}, start_line=3)
        self.assertIsNone(s.merged_context.get('foo'))
        self.assertEqual(4, s.merged_context.get('baz'))
        self.assertEqual(3, s.merged_context.get('bar'))
        s.leave(converter.Block.KIND_WITH)
        self.assertEqual(4, s.merged_context.get('baz'))
        self.assertEqual(1, s.merged_context.get('bar'))
        s.leave(converter.Block.KIND_WITH)
        self.assertIsNone(s.merged_context.get('baz'))
        self.assertEqual(1, s.merged_context.get('bar'))


class GeneratorTestCase(unittest.TestCase):
    def make_generator(self, lines, categories):
        config = converter.GeneratorConfig(
            categories=categories,
            commands=[cmd_class() for cmd_class in converter.DEFAULT_COMMANDS],
            fs=None,
        )
        return config.load(lines)

    def test_no_special(self):
        txt = [
            'foo',
            'bar',
            'baz',
        ]

        g = self.make_generator(txt, categories=[])
        expected = [converter.Line(s, s) for s in txt]
        out = list(g)
        self.assertEqual(expected, out)

    def test_nonmatching_if(self):
        txt = [
            'foo',
            '#@if blah',
            'bar',
            '#@endif',
            'baz',
        ]

        g = self.make_generator(txt, categories=['blih'])
        expected = [
            converter.Line('foo', 'foo'),
            converter.Line(None, '#@if blah'),
            converter.Line(None, 'bar'),
            converter.Line(None, '#@endif'),
            converter.Line('baz', 'baz'),
        ]
        out = list(g)
        self.assertEqual(expected, out)

    def test_unclosed_nonmatching_if(self):
        txt = [
            'foo',
            '#@if blah',
            'bar',
        ]

        g = self.make_generator(txt, categories=['blih'])
        expected = [
            converter.Line('foo', 'foo'),
            converter.Line(None, '#@if blah'),
            converter.Line(None, 'bar'),
        ]
        out = list(g)
        self.assertEqual(expected, out)

    def test_matching_if(self):
        txt = [
            'foo',
            '#@if blah',
            'bar',
            '#@endif',
            'baz',
        ]

        g = self.make_generator(txt, categories=['blah'])
        expected = [
            converter.Line('foo', 'foo'),
            converter.Line(None, '#@if blah'),
            converter.Line('bar', 'bar'),
            converter.Line(None, '#@endif'),
            converter.Line('baz', 'baz'),
        ]
        out = list(g)
        self.assertEqual(expected, out)

    def test_unclosed_matching_if(self):
        txt = [
            'foo',
            '#@if blah',
            'bar',
        ]

        g = self.make_generator(txt, categories=['blah'])
        expected = [
            converter.Line('foo', 'foo'),
            converter.Line(None, '#@if blah'),
            converter.Line('bar', 'bar'),
        ]
        out = list(g)
        self.assertEqual(expected, out)

    def test_inner_block(self):
        txt = [
            'foo',
            '#@if blah',
            'bar',
            '#@if blih',
            'barbar',
            '#@endif',
            'bazbaz',
            '#@endif',
            'baz',
        ]

        g = self.make_generator(txt, categories=['blih'])
        expected = [
            converter.Line('foo', 'foo'),
            converter.Line(None, '#@if blah'),
            converter.Line(None, 'bar'),
            converter.Line(None, '#@if blih'),
            converter.Line(None, 'barbar'),
            converter.Line(None, '#@endif'),
            converter.Line(None, 'bazbaz'),
            converter.Line(None, '#@endif'),
            converter.Line('baz', 'baz'),
        ]
        out = list(g)
        self.assertEqual(expected, out)



if __name__ == '__main__':
    unittest.main()
