# coding: utf-8
# Copyright (c) 2010-2012 Raphaël Barrois

import re


class FileProcessor(object):
    """Handles 'standard' processing of a file.

    Attributes:
        src (str list): lines of the file to process
        fs (FileSystem): abstraction toward the filesystem
    """
    def __init__(self, src, fs):
        self.src = src
        self.fs = fs

    def forward(self, categories):
        """Process the source file with an active list of categories."""
        generator = Generator(self.src, categories, self.fs)
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
        original_output = list(self.forward)
        diff = Differ(original_output, modified)
        generator = Generator(self.src, categories, self.fs)
        backporter = Backporter(diff, generator)

        for line in backporter:
            yield line


class Differ(object):
    """Computes differences between two files (as string lists).

    Based on difflib.SequenceMatcher, but yields atomic operations.

    Attributes:
        original (str list): lines of the original file
        modified (str list): lines of the modified file
    """
    def __init__(self, original, modified):
        self.original = original
        self.modified = modified

    def __iter__(self):
        """Yield atomic diff lines.

        Yields:
            (operation, new_line) tuples.
        """
        matcher = difflib.SequenceMatcher(a=original_output, b=modified)
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


class Backporter(object):
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
                action, output = diff.next()
                while action == 'insert':
                    # Inserting lines
                    # Always include, without forwarding the source
                    yield self.reverse(output)
                    action, output = diff.next()

                if action == 'delete':
                    # Deleting one line, advance the source
                    continue
                else:
                    # Replacing / equal, write the current line
                    yield self.reverse(output)

        # Handle additional lines from the diff
        # Should only be 'insert' lines.
        for action, output in diff:
            assert action == 'insert'
            yield self.reverse(output)


class Line(object):
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


class Generator(object):
    """Generate the output from a source.

    Attributes:
        src (iterable of str): the source lines
        categories (str set): the active categories
        in_block (bool): whether the generator is in a block
        in_published_block (bool): whether the current block should be published
        context (str => str dict): maps a placeholder name to its content
        fs (FileSystem): abstraction to the file system
        _current_lineno (int): the current line number
    """

    command_re = re.compile(r'^["!#]@(if|else|elif|endif|with|withfile|endwith)(?: .*)?$')
    comment_re = re.compile(r'^["!#]@#')
    escaped_re = re.compile(r'^["!#]@@')
    with_args_re = re.compile(r'^(\w+)=(.*)$')

    def __init__(self, src, categories, fs):
        self.src = src
        self.categories
        self.in_block = False
        self.in_published_block = True
        self.context = {}
        self.fs = fs

        self._current_lineno = 0

    def __iter__(self):
        for lineno, line in enumerate(self.src):
            self._current_lineno = lineno

            # Some comment
            if self.comment_re.match(line):
                yield Line(None, line)

            # An escaped line
            elif self.escaped_re.match(line):
                yield Line(line[:2] + line[3:], line)

            # A command line (dispatch to handle_command)
            elif self.command_re.match(line):
                command, args = self.command_re.match(line).groups()
                self.handle_command(command, args)
                yield Line(None, line)

            # If displaying the line, replace placeholders.
            elif self.in_published_block:
                updated_line = line
                for var, value in self.context.items():
                    pattern = '@@%s@@' % var
                    updated_line = updated_line.replace(pattern, value)
                yield Line(updated_line, line)

            # Not displaying the line
            else:
                yield Line(None, line)

    def invalid(self, message, *args):
        """Generate a contextualized error message."""
        error = "Error on line %d: " % self._current_lineno
        raise ValueError(error + message % args)

    def assert_in_block(self, command):
        """Enforce "command within a block"."""
        if not self.in_block:
            self.invalid("Invalid command '%s' outside a block", command)

    def parse_with_args(self, args):
        """Parce "#@with" arguments (and validate the line structure)."""
        match = self.with_args_re.match(args)
        if not match:
            self.invalid("Invalid 'with' argument %r", args)
        return match.groups()

    def read_file(self, filename):
        """Read one line from a file."""
        return self.fs.read_one_line(filename)

    def handle_command(self, command, args):
        """Handle a "#@<command>" line."""
        if command == 'if':
            rule = parser.parse_rule(args)
            self.in_block = True
            self.in_published_block = rule.test(self.categories)

        elif command == 'else':
            self.assert_in_block(command)

            self.in_published_block = not self.in_published_block

        elif command == 'elif':
            self.assert_in_block(command)

            if self.in_published_block:
                self.in_published_block = False
            else:
                rule = parser.parse_rule(args)
                self.in_published_block = rule.test(self.categories)

        elif command == 'endif':
            self.assert_in_block(command)

            self.in_block = False
            self.in_published_block = True

        elif command == 'with':
            var, value = self.parse_with_args(args)
            if self.in_published_block:
                self.context[var] = value

        elif command == 'withfile':
            var, filename = self.parse_with_args(args)
            if self.in_published_block:
                self.context[var] = self.read_file(filename)

        elif command == 'endwith':
            for var in args.split():
                if var in self.context:
                    del self.context[var]

        else:
            self.invalid("Invalid command '%s'", command)
