# -*- coding: utf-8 -*-
# Copyright (c) 2010-2013 Raphaël Barrois
# This software is distributed under the two-clause BSD license.

"""Handles parsing of rules."""

import tdparser


# {{{ Nodes

class _ConditionNode:
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


class _TextToken(tdparser.Token):
    lbp = 25
    regexp = r'[a-zA-Z0-9._-]+'

    def __init__(self, text):
        self.text = text

    def nud(self, context):
        return _TextNode(self.text)

    def led(self, left, context):
        return _OrNode([left, _TextNode(self.text)])

    def __repr__(self):
        return '<Text: %r>' % self.text


class _OrToken(tdparser.Token):
    lbp = 10
    regexp = r'\|\|'

    def led(self, left, context):
        right = context.expression(self.lbp)
        return _OrNode([left, right])

    def __repr__(self):
        return '<Or>'


class _AndToken(tdparser.Token):
    lbp = 15
    regexp = r'&&'

    def led(self, left, context):
        right = context.expression(self.lbp)
        return _AndNode([left, right])

    def __repr__(self):
        return '<And>'


class _NotToken(tdparser.Token):
    lbp = 10
    regexp = r'!'

    def nud(self, context):
        return _NegateNode(context.expression(100))

    def __repr__(self):
        return '<Not>'


# }}}
# {{{ Lexer


class RuleLexer:
    """Build a rule lexer

    Some possible patterns:
    a b c => Matches if any of a, b, c
    a || b || c
    a || (b && !c) => Matches if a or (b and not c)
    """
    def __init__(self):
        self.lexer = self._build_lexer()

    @classmethod
    def _build_lexer(cls):
        lexer = tdparser.Lexer(with_parens=True)
        lexer.register_tokens(_TextToken, _OrToken, _AndToken, _NotToken)
        return lexer

    def get_rule(self, text):
        return Rule(text, self.lexer.parse(text))

# }}}
# {{{ Rule


class Rule:
    def __init__(self, text, node):
        self.text = text
        self.node = node

    def test(self, categories):
        """Test whether a set of categories match this rule.

        Args:
            categories (str set): categories to test

        Returns:
            bool
        """
        return self.node.eval(categories)

    def __repr__(self):
        return "Rule(%r)" % self.text

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.node == other.node

# }}}
