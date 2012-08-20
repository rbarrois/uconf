# coding: utf-8
# Copyright (c) 2010-2012 Raphaël Barrois

import unittest

from confmgr import converter


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


class GeneratorTestCase(unittest.TestCase):
    def test_no_special(self):
        txt = [
            'foo',
            'bar',
            'baz',
        ]

        g = converter.Generator(txt, categories=[], fs=None)
        expected = [converter.Line(s, s) for s in txt]
        out = list(g)
        self.assertItemsEqual(expected, out)

    def test_nonmatching_if(self):
        txt = [
            'foo',
            '#@if blah',
            'bar',
            '#@endif',
            'baz',
        ]

        g = converter.Generator(txt, categories=['blih'], fs=None)
        expected = [
            converter.Line('foo', 'foo'),
            converter.Line(None, '#@if blah'),
            converter.Line(None, 'bar'),
            converter.Line(None, '#@endif'),
            converter.Line('baz', 'baz'),
        ]
        out = list(g)
        self.assertItemsEqual(expected, out)

    def test_unclosed_nonmatching_if(self):
        txt = [
            'foo',
            '#@if blah',
            'bar',
        ]

        g = converter.Generator(txt, categories=['blih'], fs=None)
        expected = [
            converter.Line('foo', 'foo'),
            converter.Line(None, '#@if blah'),
            converter.Line(None, 'bar'),
        ]
        out = list(g)
        self.assertItemsEqual(expected, out)

    def test_matching_if(self):
        txt = [
            'foo',
            '#@if blah',
            'bar',
            '#@endif',
            'baz',
        ]

        g = converter.Generator(txt, categories=['blah'], fs=None)
        expected = [
            converter.Line('foo', 'foo'),
            converter.Line(None, '#@if blah'),
            converter.Line('bar', 'bar'),
            converter.Line(None, '#@endif'),
            converter.Line('baz', 'baz'),
        ]
        out = list(g)
        self.assertItemsEqual(expected, out)

    def test_unclosed_matching_if(self):
        txt = [
            'foo',
            '#@if blah',
            'bar',
        ]

        g = converter.Generator(txt, categories=['blah'], fs=None)
        expected = [
            converter.Line('foo', 'foo'),
            converter.Line(None, '#@if blah'),
            converter.Line('bar', 'bar'),
        ]
        out = list(g)
        self.assertItemsEqual(expected, out)


if __name__ == '__main__':
    unittest.main()
