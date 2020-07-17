# -*- coding: utf-8 -*-
# Copyright (c) 2010-2013 Raphaël Barrois
# This software is distributed under the two-clause BSD license.

import difflib
import re

from uconf import rule_parser


class CommandError(Exception):
    pass


class FileProcessor:
    """Handles 'standard' processing of a file.

    Attributes:
        src (str list): lines of the file to process
        fs (FileSystem): abstraction toward the filesystem
    """
    def __init__(self, src, fs):
        self.src = list(src)
        self.fs = fs

    def _get_gen_config(self, categories):
        return GeneratorConfig(
            categories=categories,
            commands=[cmd() for cmd in DEFAULT_COMMANDS],
            fs=self.fs,
        )

    def forward(self, categories):
        """Process the source file with an active list of categories."""
        gen_config = self._get_gen_config(categories)
        generator = gen_config.load(self.src)
        for line in generator:
            if line.output is not None:
                yield line.output

    def backward(self, categories, modified):
        """Revert a file.

        Args:
            categories (str iterable): active categories
            modified (str list): lines of the modified file

        Yields:
            str: updated lines for the original file
        """
        categories = frozenset(categories)
        original_output = self.forward(categories)
        diff = Differ(original_output, modified)
        gen_config = self._get_gen_config(categories)
        generator = gen_config.load(self.src)
        backporter = Backporter(diff, generator)

        for line in backporter:
            yield line


class Differ:
    """Computes differences between two files (as string lists).

    Based on difflib.SequenceMatcher, but yields atomic operations.

    Attributes:
        original (str list): lines of the original file
        modified (str list): lines of the modified file
    """
    def __init__(self, original, modified):
        self.original = list(original)
        self.modified = list(modified)

    def __iter__(self):
        """Yield atomic diff lines.

        Yields:
            (operation, new_line) tuples.
        """
        matcher = difflib.SequenceMatcher(a=self.original, b=self.modified)
        opcodes = matcher.get_opcodes()
        for opcode, original_i, original_j, modified_i, modified_j in opcodes:
            if opcode == 'equal':
                for original_lineno in range(original_i, original_j):
                    yield (opcode, self.original[original_lineno])
            elif opcode == 'insert':
                for modified_lineno in range(modified_i, modified_j):
                    yield (opcode, self.modified[modified_lineno])
            elif opcode == 'delete':
                for original_lineno in range(original_i, original_j):
                    yield (opcode, self.original[original_lineno])
            elif opcode == 'replace':
                common = min(original_j - original_i, modified_j - modified_i)
                for modified_lineno in range(modified_i, modified_i + common):
                    yield (opcode, self.modified[modified_lineno])
                for modified_lineno in range(modified_i + common, modified_j):
                    yield ('insert', self.modified[modified_lineno])
                for original_lineno in range(original_i + common, original_j):
                    yield ('delete', self.original[original_lineno])


class Backporter:
    """Handles the backporting of a diff to an original file.

    Attributes:
        diff ((operation, new_line) iterable): the lines of the diff
        source (Line iterable): the lines of the source
    """

    def __init__(self, diff, source):
        self.diff = diff
        self.source = source

    def reverse(self, output):
        """Convert back an output line into its original version."""
        line = Line(output, None)
        line.fill_original()
        return line.original

    def __iter__(self):
        """Yield lines from the initial file."""
        diff = iter(self.diff)

        for line in self.source:
            # Loop through the generated lines

            if line.output is None:
                # Masked line (comment, command)
                # Always include
                yield line.original

            else:
                action, output = next(diff)
                while action == 'insert':
                    # Inserting lines
                    # Always include, without forwarding the source
                    yield self.reverse(output)
                    action, output = next(diff)

                if action == 'delete':
                    # Deleting one line, advance the source
                    continue
                elif action == 'equal':
                    # No change
                    yield line.original
                else:
                    assert action == "replace"
                    # Backport the resulting line
                    yield self.reverse(output)

        # Handle additional lines from the diff
        # Should only be 'insert' lines.
        for action, output in diff:
            assert action == 'insert', "Unexpected action %s on %r" % (action, output)
            yield self.reverse(output)


class Line:
    def __init__(self, output, original):
        self.output = output
        self.original = original

    def __repr__(self):
        return "Line(%r, %r)" % (self.output, self.original)

    def __hash__(self):
        return hash((self.output, self.original))

    def __eq__(self, other):
        if not isinstance(other, Line):
            return NotImplemented
        return self.output == other.output and self.original == other.original

    def fill_original(self):
        """Fill the 'original' part from the output."""
        if self.original is not None:
            return

        # If the output line looks like a comment or command, escape it.
        should_escape_re = re.compile(r'^["!#]@')
        if should_escape_re.match(self.output):
            self.original = '%s@%s' % (
                self.output[:2],
                self.output[2:],
            )
        else:
            self.original = self.output


class Block:
    KIND_IF = 'if'
    KIND_WITH = 'with'

    def __init__(self, kind, start_line, published=True, context=None):
        self.kind = kind
        self.published = published
        self.context = context or {}
        self.start_line = start_line

    def __repr__(self):
        return "Block(%r, %d, %r, %r)" % (
            self.kind,
            self.start_line,
            self.published,
            self.context,
        )


class BlockStack:
    def __init__(self):
        self.blocks = []

    def __nonzero__(self):
        return bool(self.blocks)

    def __len__(self):
        return len(self.blocks)

    def __repr__(self):
        return "<BlockStack: %r>" % self.blocks

    @property
    def published(self):
        return all(b.published for b in self.blocks)

    @property
    def merged_context(self):
        context = {}
        for block in self.blocks:
            context.update(block.context)
        return context

    def enter(self, *args, **kwargs):
        block = Block(*args, **kwargs)
        self.blocks.append(block)
        return block

    def leave(self, kind):
        if not self.blocks:
            raise ValueError("Not inside a block.")
        last_kind = self.blocks[-1].kind
        if last_kind != kind:
            raise ValueError("Unexpected last block kind: %s!=%s." % (last_kind, kind))
        return self.blocks.pop()


class BaseCommand:
    """A command.

    Entry points: get_keys(), handle(...).
    """
    keys = ()

    def get_keys(self):
        """Return the list of "keys" (or "commands") handled by this class."""
        return self.keys

    def handle(self, key, argline, state, config):
        """Handle a line.

        Args:
            key (str): one of the keys in get_keys()
            argline (str): everything after the key and a space
            state (GeneratorState): the current state of the generator
            config (GeneratorConfig): various config-time params of the generator
        """
        raise NotImplementedError()


class BaseBlockCommand(BaseCommand):
    enter_keys = ()
    inside_keys = ()
    exit_keys = ()

    def get_keys(self):
        return self.enter_keys + self.inside_keys + self.exit_keys

    def handle(self, key, argline, state, config):
        if key in self.enter_keys:
            return self.enter(key, argline, state, config)
        elif key in self.inside_keys:
            return self.inside(key, argline, state, config)
        else:
            assert key in self.exit_keys
            return self.exit(key, argline, state, config)

    def enter(self, key, argline, state, config):
        raise NotImplementedError()

    def inside(self, key, argline, state, config):
        raise NotImplementedError()

    def exit(self, key, argline, state, config):
        raise NotImplementedError()


class IfBlockCommand(BaseBlockCommand):
    enter_keys = ('if',)
    inside_keys = ('else', 'elif')
    exit_keys = ('endif',)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.rule_lexer = rule_parser.RuleLexer()

    def enter(self, key, argline, state, config):
        rule = self.rule_lexer.get_rule(argline)
        state.enter_block(Block.KIND_IF, published=rule.test(config.categories))

    def inside(self, key, argline, state, config):
        if key == 'else':
            if argline:
                state.error("Command 'else' takes no argument, got %r", argline)

            last_block = state.leave_block(Block.KIND_IF)
            state.enter_block(Block.KIND_IF, published=not last_block.published)
        else:
            assert key == 'elif'
            last_block = state.leave_block(Block.KIND_IF)
            if last_block.published:
                published = False
            else:
                rule = self.rule_lexer.get_rule(argline)
                published = rule.test(config.categories)

            state.enter_block(Block.KIND_IF, published=published)

    def exit(self, key, argline, state, config):
        assert key == 'endif'
        if argline:
            state.error("Command 'endif' takes no argument, got %r", argline)
        state.leave_block(Block.KIND_IF)


class WithBlockCommand(BaseBlockCommand):
    enter_keys = ('with', 'withfile')
    exit_keys = ('endwith',)

    with_args_re = re.compile(r'^(\w+)=(.*)$')

    def _read_file(self, filename, config):
        """Read one line from a file."""
        return config.fs.read_one_line(filename)

    def _parse_with_args(self, args, state):
        """Parce "#@with" arguments (and validate the line structure)."""
        match = self.with_args_re.match(args)
        if not match:
            state.error("Invalid 'with' argument %r", args)
        return match.groups()

    def enter(self, key, argline, state, config):
        if key == 'with':
            var, value = self._parse_with_args(argline, state=state)
            state.enter_block(Block.KIND_WITH, context={var: value})
        else:
            assert key == 'withfile'
            var, filename = self._parse_with_args(argline, state=state)
            value = self._read_file(filename, config)
            state.enter_block(Block.KIND_WITH, context={var: value})

    def exit(self, key, argline, state, config):
        last_block = state.leave_block(Block.KIND_WITH)
        if argline and argline not in last_block.context:
            raise CommandError(
                "Block mismatch: closing 'with' block from line %d with invalid variable %r"
                % (last_block.start_line, argline),
            )


class GeneratorState:
    """Handles the internal generator state.

    Attributes:
        in_published_block (bool): whether the current block should be published
        context (str => str dict): maps a placeholder name to its content
        _current_lineno (int): the current line number
    """

    def __init__(self):
        self.block_stack = BlockStack()
        self._current_lineno = 0

    @property
    def in_published_block(self):
        return self.block_stack.published

    @property
    def context(self):
        return self.block_stack.merged_context

    def error(self, message, *args):
        err_msg = "Error on line %d: " % self._current_lineno
        raise ValueError((err_msg + message) % args)

    def advance_to(self, lineno):
        self._current_lineno = lineno

    def enter_block(self, kind, published=True, context=None):
        return self.block_stack.enter(
            kind=kind,
            published=published,
            context=context,
            start_line=self._current_lineno,
        )

    def leave_block(self, kind):
        try:
            return self.block_stack.leave(kind)
        except ValueError as e:
            self.invalid("Error when closing block: %r", e)


DEFAULT_COMMANDS = [
    IfBlockCommand,
    WithBlockCommand,
]


class Generator:
    """Generate the output from a source.

    Attributes:
        src (iterable of str): the source lines
        state (GeneratorState): the current generator state
    """

    command_prefix_re = re.compile(r'^(["!#]@)(.+)$')

    def __init__(self, src, commands, config):
        self.src = src
        self.config = config
        self.state = GeneratorState()
        self.commands_by_key = {}
        for command in commands:
            for key in command.get_keys():
                if key in self.commands_by_key:
                    raise ValueError(
                        "Duplicate command for key %s: got %r and %r"
                        % (key, command, self.commands_by_key[key]),
                    )
                self.commands_by_key[key] = command

    def __iter__(self):
        for lineno, line in enumerate(self.src):
            self.state.advance_to(lineno)

            match = self.command_prefix_re.match(line)
            if match:
                prefix, command = match.groups()
                output = self.handle_line(prefix, command)

            # If displaying the line, replace placeholders.
            elif self.state.in_published_block:
                updated_line = line
                for var, value in self.state.context.items():
                    pattern = '@@%s@@' % var
                    updated_line = updated_line.replace(pattern, value)
                output = updated_line

            # Not displaying the line
            else:
                output = None

            yield Line(output, line)

    def handle_line(self, prefix, command):
        if command.startswith('#'):
            # A comment
            return None

        elif command.startswith('@'):
            # An escaped line
            return prefix + command[1:]

        else:
            if ' ' in command:
                name, args = command.split(' ', 1)
            else:
                name, args = command, ''
            self.handle_command(name, args)
            return None

    def handle_command(self, command, args):
        """Handle a "#@<command>" line."""
        if command not in self.commands_by_key:
            raise CommandError("Unknown command '%s' (not in %r)" % (command, sorted(self.commands_by_key)))

        handler = self.commands_by_key[command]
        handler.handle(command, args, self.state, self.config)


class GeneratorConfig:
    def __init__(self, categories, commands, fs, generator=Generator):
        self.categories = categories
        self.commands = commands
        self.fs = fs
        self.fs_root = '/'
        self.generator_class = generator

    def load(self, source_file):
        return self.generator_class(
            source_file,
            config=self,
            commands=self.commands,
        )
