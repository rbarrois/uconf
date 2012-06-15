# coding: utf-8
# Copyright (c) 2010-2012 Raphaël Barrois


class Converter(object):
    def __init__(self, src, root):
        self.src = src
        self.root = root

    def forward(self, categories):
        generator = Generator(self.src)
        for line in generator:
            if line.output:
                yield line.output

    def backward(self, categories, modified):
        pass


class Line(object):
    def __init__(self, output, original):
        self.output = output
        self.original = original

    def fill_original(self):
        """Fill the 'original' part from the output."""
        if self.original is not None:
            return

        # If the output line looks like a comment or command, escape it.
        hould_escape_re = re.compile(r'^["!#]@')
        if should_escape_re.match(self.output):
            self.original = '%s@%s' % (
                self.output[:2],
                self.output[2:],
            )


class Generator(object):
    """Generate the output from a source.

    Attributes:
        src (iterable of str): the source lines
        categories (str set): the active categories
        in_block (bool): whether the generator is in a block
        in_published_block (bool): whether the current block should be published
        context (str => str dict): maps a placeholder name to its content
        root (str): the root of the filesystem
        _current_lineno (int): the current line number
    """

    command_re = re.compile(r'^["!#]@(if|else|elif|endif|with|withfile|endwith)(?: .*)?$')
    comment_re = re.compile(r'^["!#]@#')
    escaped_re = re.compile(r'^["!#]@@')
    with_args_re = re.compile(r'^(\w+)=(.*)$')

    def __init__(self, src, categories, root='.'):
        self.src = src
        self.categories
        self.in_block = False
        self.in_published_block = True
        self.context = {}
        self.root = root

        self._current_lineno = 0

    def __iter__(self):
        for lineno, line in enumerate(self.src):
            self._current_lineno = lineno

            # Some comment
            if self.comment_re.match(line):
                yield Line('', line, False)

            # An escaped line
            elif self.escaped_re.match(line):
                yield Line(line[:2] + line[3:], line, False)

            # A command line (dispatch to handle_command)
            elif self.command_re.match(line):
                command, args = self.command_re.match(line).groups()
                self.handle_command(command, args)
                yield Line('', line)

            # If displaying the line, replace placeholders.
            elif self.in_published_block:
                updated_line = line
                for var, value in self.context.items():
                    pattern = '@@%s@@' % var
                    updated_line = updated_line.replace(pattern, value)
                yield Line(updated_line, line)

            # Not displaying the line
            else:
                yield Line('', line)

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
        # TODO(rbarrois): move to a help method on a filesystem abstraction
        # layer
        with open(os.path.join(self.root, filename)) as f:
            return f.readline().strip()

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
