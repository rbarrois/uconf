# coding: utf-8
# Copyright (c) 2010-2012 Raphaël Barrois

"""Handles parsing of rules."""

import re


class _ConditionNode(object):
    """Base class for a node."""
    precedence = 0

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


class _FalseNode(_ConditionNode):
    """A 'false' node."""
    def eval(self, atoms):
        return False

    def __repr__(self):
        return '<False>'


class _TrueNode(_ConditionNode):
    """A 'true' node."""
    def eval(self, atoms):
        return True

    def __repr__(self):
        return '<True>'


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


class _OrNode(_MultiNode):
    """A 'or' node."""
    precedence = 10

    def eval(self, atoms):
        return any(son.eval(atoms) for son in self.sons)

    def __repr__(self):
        return '<Or%r>' % (tuple(self.sons),)


class _Token(object):
    """Base class for tokens.

    Ref:
        http://effbot.org/zone/simple-top-down-parsing.htm
        http://javascript.crockford.com/tdop/tdop.html
    """

    # Left binding power
    # Controls how much this token binds to a token on its right
    lbp = 0

    def __init__(self, text=None):
        pass

    def nud(self):
        """Null denotation.

        Describes what happens to this token when located at the beginning of
        an expression.

        Returns:
            _ConditionNode: the node representing this token
        """
        raise NotImplementedError()

    def led(self, left, context):
        """Left denotation.

        Describe what happens to this token when appearing inside a construct
        (at the left of the rest of the construct).

        Args:
            context (_Parser): the parser from which 'next' data can be
                retrieved
            left (_ConditionNode): the representation of the construct on the
                left of this token

        Returns:
            _ConditionNode built from this token, what is on its right, and
                what was on its left.
        """
        raise NotImplementedError()


class _TextToken(_Token):

    def __init__(self, text):
        self.text = text

    def nud(self, context):
        return _TextNode(self.text)

    def __repr__(self):
        return '<Text: %r>' % self.text


class _OrToken(_Token):
    lbp = 10

    def led(self, left, context):
        right = context.expression(self.lbp)
        return _OrNode([left, right])

    def __repr__(self):
        return '<Or>'

class _AndToken(_Token):
    lbp = 15

    def led(self, left, context):
        right = context.expression(self.lbp)
        return _AndNode([left, right])

    def __repr__(self):
        return '<And>'


class _NotToken(_Token):
    lbp = 10

    def nud(self, context):
        return _NegateNode(context.expression(100))

    def __repr__(self):
        return '<Not>'


class _LeftParen(_Token):
    def nud(self, context):
        expr = context.expression()
        context.advance(expect_class=_RightParen)
        return expr


class _RightParen(_Token):
    pass


class _EndToken(_Token):
    """Marks the end of the input."""
    lbp = 0

    def __repr__(self):
        return '<End>'


class _Parser(object):
    """Converts lexed tokens into a _ConditionNode.

    Attributes:
        tokens (iterable of str): the tokens.
    """

    def __init__(self, tokens):
        self.tokens = tokens
        self.current_token = self.tokens[0]
        self._cur_token = 0

    def advance(self, expect_class=None):
        """Retrieve the next token."""
        if expect_class:
            assert self.current_token.__class__ == expect_class

        self._cur_token += 1
        self.current_token = self.tokens[self._cur_token]
        return self.current_token

    def expression(self, rbp=0):
        """Extract an expression from the flow of tokens.

        TODO: explain rbp.
        """
        prev_token = self.current_token
        self.advance()

        # Retrieve the _ConditionNode from the previous token situated at the
        # leftmost point in the expression
        left = prev_token.nud(context=self)

        while rbp < self.current_token.lbp:
            # Read incoming tokens with a higher 'left binding power'.
            # Those are tokens that prefer binding to the left of an expression
            # than to the right of an expression.
            prev_token = self.current_token
            self.advance()
            left = prev_token.led(left, context=self)

        return left

    def parse(self):
        return self.expression()


class Rule(object):
    """A rule.

    Some possible patterns:
    a b c => Matches if any of a, b, c
    a || b || c
    a || (b && !c) => Matches if a or (b and not c)

    Attributes:
        text (str): the text of the rule
    """
    ATOM_NAME_RE = re.compile(r'^[a-z._-]+$')

    TOKENS = (
        (_TextToken, re.compile(r'[a-z._-]+')),
        (_OrToken, re.compile(r'\|\|')),
        (_AndToken, re.compile(r'&&')),
        (_NotToken, re.compile(r'!')),
        (_LeftParen, re.compile(r'\(')),
        (_RightParen, re.compile(r'\)')),
    )

    def __init__(self, text, *args, **kwargs):
        self.text = text
        super(Rule, self).__init__(*args, **kwargs)

    def _get_token(self, text):
        """Retrieve the next token from some text.

        Args:
            text (str): the text from which tokens should be extracted

        Returns:
            (token_kind, token_text): the token kind and its content.
        """
        for (kind, regexp) in self.TOKENS:
            match = regexp.match(text)
            if match:
                return kind, match
        return None, None

    def _split_tokens(self):
        """Split self.text into a list of tokens.

        Returns:
            list of (str, str): the list of (token kind, token text) generated
                from self.text.
        """
        text = self.text

        tokens = []

        while text:
            kind, match = self._get_token(text)
            if kind:
                tokens.append((kind(text[match.start():match.end()])))
                text = text[match.end():]
            elif text[0] in (' ', '\t'):
                text = text[1:]
            else:
                raise ValueError('Invalid character %s in %s' % (text[0], text))

        tokens.append(_EndToken())
        return tokens

    def parse(self):
        """Parse self.text.

        Returns:
            _ConditionNode: a node representing the current rule.
        """
        parser = _Parser(self._split_tokens())
        return parser.parse()
