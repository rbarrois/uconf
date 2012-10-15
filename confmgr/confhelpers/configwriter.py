class ConfigLine(object):
    """A simple config line."""
    KIND_BLANK = 0
    KIND_COMMENT = 1
    KIND_DATA = 2

    def __init__(self, kind, key=None, value=None, text=None):
        self.kind = kind
        self.key = key
        self.value = value
        self.text = text

    def match(self, other):
        if other.kind != self.kind:
            return False
        if self.kind == self.KIND_DATA:
            return self.key == other.key and (other.value is None or other.value == self.value)
        else:
            return self.text == other.text

    def __str__(self):
        if self.kind == self.KIND_DATA:
            return '%s: %r' % (self.key, self.value)
        else:
            return self.text

    def __repr__(self):
        return 'ConfigLine(%r, %r, %r, %r)' % (self.kind, self.key,
                self.value, self.text)

    def __eq__(self, other):
        if not isinstance(other, ConfigLine):
            return NotImplemented

        return ((self.kind, self.key, self.value, self.text)
            == (other.kind, other.key, other.value, other.text))

    def __hash__(self):
        return hash((self.kind, self.key, self.value, self.text))


class ConfigLineList(object):
    def __init__(self, *lines):
        self.lines = list(lines)

    def append(self, line):
        self.lines.append(line)

    def find_lines(self, line):
        """Find all lines matching a given line."""
        for other_line in self.lines:
            if other_line.match(line):
                yield other_line

    def remove(self, line):
        self.lines = [l for l in self.lines if not l.match(line)]

    def update(self, old_line, new_line, once=False):
        """Replace all lines matching `old_line` with `new_line`.

        If ``once`` is set to True, remove only the first instance.
        """
        for i, line in enumerate(self.lines):
            if line.match(old_line):
                self.lines[i] = new_line
                if once:
                    return

    def __contains__(self, line):
        return any(self.find_lines(line))

    def __len__(self):
        return len(self.lines)

    def __iter__(self):
        return iter(self.lines)

    def __eq__(self, other):
        if not isinstance(other, ConfigLineList):
            return NotImplemented
        return self.lines == other.lines

    def __hash__(self):
        return hash((self.__class__, self.lines))

    def __repr__(self):
        return 'ConfigLineList(%r)' % self.lines


class SectionBlock(object):
    """A section block.

    A section's content may be spread across many such blocks in the file.
    """
    def __init__(self, name, written=True):
        self.name = name
        self.is_written = written
        self.lines = ConfigLineList()

    def insert(self, line):
        self.lines.append(line)

    def __contains__(self, line):
        return line in self.lines

    def update(self, old_line, new_line, once=False):
        """Replace all lines matching `old_line` with `new_line`.

        If ``once`` is set to True, remove only the first instance.
        """
        self.lines.update(old_line, new_line, once=once)

    def remove(self, line):
        """Remove all instances of a line."""
        self.lines.remove(line)

    def __iter__(self):
        return iter(self.lines)


class Section(object):
    """A section.

    A section has a ``name`` and lines spread around the file.
    """
    def __init__(self, name):
        self.name = name
        self.blocks = []

    @property
    def extra_block(self):
        if self.blocks and not self.blocks[-1].is_written:
            return self.blocks[-1]

    def new_block(self, **kwargs):
        block = SectionBlock(self.name, **kwargs)
        self.blocks.append(block)
        return block

    def insert(self, line):
        block = self.find_block(line)
        if not block:
            if self.blocks:
                block = self.blocks[-1]
            else:
                block = self.new_block(written=False)
        block.insert_line(line)

    def update(self, old_line, new_line, once=False):
        """Replace all lines matching `old_line` with `new_line`.

        If ``once`` is set to True, remove only the first instance.
        """
        for block in self.blocks:
            block.update(old_line, new_line, once=once)

    def remove(self, line):
        """Delete all lines matching the given line."""
        for block in self.blocks:
            block.remove(line)

    def __iter__(self):
        return iter(self.blocks)


class ConfigFile(object):
    """A (hopefully writable) config file.

    Attributes:
        sections (dict(name => Section)): sections of the file
        blocks (SectionBlock list): blocks from the file
        header (ConfigLineList): list of lines before the first section
        current_block (SectionBlock): current block being read
    """

    def __init__(self):
        self.sections = dict()
        self.blocks = []
        self.header = ConfigLineList()
        self.current_block = None

    def get_section(self, name, create=True):
        """Retrieve a section by name. Create it on first access."""
        try:
            return self.sections[name]
        except KeyError:
            if not create:
                raise

            section = Section(name)
            self.sections[name] = section
            return section

    def enter_block(self, name):
        """Mark 'entering a block'."""
        section = self.get_section(name)
        block = self.current_block = sectino.new_block()
        self.blocks.append(block)

    def insert_line(self, line):
        """Insert a new line"""
        if self.current_block:
            self.current_block.insert_line(line)
        else:
            self.header.append(line)

    def insert(self, section, line):
        self.get_section(section).insert(line)

    def update(self, section, old_line, new_line, once=False):
        """Replace all lines matching `old_line` with `new_line`.

        If ``once`` is set to True, remove only the first instance.
        """
        self.get_section(section).update(new_line, old_line, once=once)

    def remove(self, section, line):
        self.get_section(section, create=False).unset(line)

    def __iter__(self):
        for line in self.header:
            yield line
        for block in self.blocks:
            for line in block:
                yield line

        for section in self.sections.values():
            if section.extra_block:
                for line in section.extra_block:
                    yield line
