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
        return '<And(%s)>' % self.sons


class _OrNode(_MultiNode):
    """A 'or' node."""
    precedence = 10

    def eval(self, atoms):
        return any(son.eval(atoms) for son in self.sons)

    def __repr__(self):
        return '<Or(%s)>' % self.sons


class _Lexer(object):
    """Converts parsed tokens into a _ConditionNode.

    Attributes:
        tokens (iterable of str): the tokens.
    """

    KIND_NOT = 'not'
    KIND_OR = 'or'
    KIND_AND = 'and'
    KIND_NAME = 'name'
    KIND_LEFT_BRACKET = 'left_bracket'
    KIND_RIGHT_BRACKET = 'right_bracket'

    def __init__(self, tokens):
        self.tokens = tokens

    def _lex(self, tokens, prev_node=None):
        """Lex a set of tokens.

        Args:
            tokens (iterable of tokens): tokens to parse
            prev_node (_ConditionNode): previously generated node

        Returns:
            (_ConditionNode, token list): the next node, and a list of remaining
                tokens
        """
        if not tokens:
            return prev_node, []

        kind, value = tokens.pop(0)
        print "Parsing %s/%s, prev=%s" % (kind, value, prev_node)
        if kind == self.KIND_NOT:
            next_node, tokens = self._lex(tokens)
            return _NegateNode(next_node), tokens
        elif kind == self.KIND_LEFT_BRACKET:
            return self._lex(tokens, prev_node)
        elif kind == self.KIND_RIGHT_BRACKET:
            assert prev_node is not None
            return prev_node, tokens
        elif kind == self.KIND_OR:
            assert prev_node is not None
            next_node, tokens = self._lex(tokens)
            return _OrNode([prev_node, next_node]), tokens
        elif kind == self.KIND_AND:
            assert prev_node is not None
            next_node, tokens = self._lex(tokens)
            return _AndNode([prev_node, next_node]), tokens
        else:  # KIND_NAME
            text_node = _TextNode(value)
            if prev_node:
                # handling "foo bar"
                text_node = _OrNode([prev_node, text_node])
            return self._lex(tokens, text_node)

    def lex(self):
        """Lex the current list of tokens.

        Returns:
            _ConditionNode: the node representing the expression.
        """
        tokens = list(self.tokens)
        cur_node = None
        while tokens:
            print "cur_node=%s, tokens=%s" % (cur_node, tokens)
            cur_node, tokens = self._lex(tokens, cur_node)
        return cur_node


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

    TOKENS = {
        'name': re.compile(r'[a-z._-]+'),
        'or': re.compile(r'\|\|'),
        'and': re.compile(r'&&'),
        'not': re.compile(r'!'),
        'left_bracket': re.compile(r'\('),
        'right_bracket': re.compile(r'\)'),
    }

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
        for (kind, regexp) in self.TOKENS.iteritems():
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
                tokens.append((kind, text[match.start():match.end()]))
                text = text[match.end():]
            elif text[0] in (' ', '\t'):
                text = text[1:]
            else:
                raise ValueError('Invalid character %s in %s' % (text[0], text))
        return tokens

    def parse(self):
        """Parse self.text.

        Returns:
            _ConditionNode: a node representing the current rule.
        """
        lexer = _Lexer(self._split_tokens())
        return lexer.lex()
