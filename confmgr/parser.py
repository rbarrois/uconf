# coding: utf-8
# Copyright (c) 2010-2012 Raphaël Barrois

"""Handles parsing of rules."""

import re

from . import topdown_parser


# {{{ Nodes

class _ConditionNode(object):
    """Base class for a node."""

    def eval(self, atoms):
        """Evaluate this node with a given set of atoms.

        Returns a boolean.
        """
        raise NotImplementedError()

    def simplify(self):
        """Simplify the current node (for easier representation).

        Returns an equivalent node.
        """
        return self

    def __eq__(self, other):
        if not isinstance(other, _ConditionNode):
            return NotImplemented

        return repr(self.simplify()) == repr(other.simplify())


class _FalseNode(_ConditionNode):
    """A 'false' node."""
    def eval(self, atoms):
        return False

    def __repr__(self):
        return '<False>'

    def __str__(self):
        return 'False'


class _TrueNode(_ConditionNode):
    """A 'true' node."""
    def eval(self, atoms):
        return True

    def __repr__(self):
        return '<True>'

    def __str__(self):
        return 'True'


class _TextNode(_ConditionNode):
    """A 'text' node.

    Attributes:
        text (str): the atom contained in the node.
    """

    def __init__(self, text):
        self.text = text

    def eval(self, atoms):
        return self.text in atoms

    def __repr__(self):
        return '<%s>' % self.text

    def __str__(self):
        return self.text


class _NegateNode(_ConditionNode):
    """A 'not' node.

    Attributes:
        son (_ConditionNode): the negated node.
    """

    precedence = 30

    def __init__(self, son):
        self.son = son

    def eval(self, atoms):
        return not self.son.eval(atoms)

    def simplify(self):
        self.son = self.son.simplify()
        return self

    def __repr__(self):
        return '<Not %s>' % self.son

    def __str__(self):
        return '! %s' % self.son


class _MultiNode(_ConditionNode):
    """An abstract node with many sons.

    Attributes:
        sons (iterable of _ConditionNode): the sons of this node.
    """

    def __init__(self, sons):
        self.sons = sons

    def simplify(self):
        """Merge all sons if possible."""

        if len(self.sons) == 1:
            # Only one son, return it (simplified)
            return self.sons[0].simplify()

        new_sons = []
        for son in self.sons:
            # Simplify sons
            son = son.simplify()
            if son.__class__ == self.__class__:
                # If they are instances of this node, merge their sons too
                new_sons.extend(son.sons)
            else:
                new_sons.append(son)
        self.sons = new_sons
        return self


class _AndNode(_MultiNode):
    """A 'and' node."""
    precedence = 20

    def eval(self, atoms):
        return all(son.eval(atoms) for son in self.sons)

    def __repr__(self):
        return '<And%r>' % (tuple(self.sons),)

    def __str__(self):
        return ' && '.join(
            ('(%s)' % son if isinstance(son, _MultiNode) else str(son))
            for son in self.sons)


class _OrNode(_MultiNode):
    """A 'or' node."""
    precedence = 10

    def eval(self, atoms):
        return any(son.eval(atoms) for son in self.sons)

    def __repr__(self):
        return '<Or%r>' % (tuple(self.sons),)

    def __str__(self):
        return ' || '.join(
            ('(%s)' % son if isinstance(son, _MultiNode) else str(son))
            for son in self.sons)


# }}}
# {{{ Tokens


class _TextToken(topdown_parser.Token):
    lbp = 25

    def __init__(self, text):
        self.text = text

    def nud(self, context):
        return _TextNode(self.text)

    def led(self, left, context):
        return _OrNode([left, _TextNode(self.text)])

    def __repr__(self):
        return '<Text: %r>' % self.text


class _OrToken(topdown_parser.Token):
    lbp = 10

    def led(self, left, context):
        right = context.expression(self.lbp)
        return _OrNode([left, right])

    def __repr__(self):
        return '<Or>'

class _AndToken(topdown_parser.Token):
    lbp = 15

    def led(self, left, context):
        right = context.expression(self.lbp)
        return _AndNode([left, right])

    def __repr__(self):
        return '<And>'


class _NotToken(topdown_parser.Token):
    lbp = 10

    def nud(self, context):
        return _NegateNode(context.expression(100))

    def __repr__(self):
        return '<Not>'


# }}}
# {{{ Lexer


class RuleLexer(topdown_parser.Lexer):
    """A rule lexer.

    Some possible patterns:
    a b c => Matches if any of a, b, c
    a || b || c
    a || (b && !c) => Matches if a or (b and not c)

    Attributes:
        text (str): the text of the rule
    """

    TOKENS = topdown_parser.Lexer.TOKENS + (
        (_TextToken, re.compile(r'[a-z._-]+')),
        (_OrToken, re.compile(r'\|\|')),
        (_AndToken, re.compile(r'&&')),
        (_NotToken, re.compile(r'!')),
    )

# }}}
