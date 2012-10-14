class ConfigLine(object):
    KIND_BLANK = 0
    KIND_COMMENT = 1
    KIND_DATA = 2

    def __init__(self, kind, key=None, value=None):
        self.kind = kind
        self.key = key
        self.value = value


class SectionBlock(object):
    def __init__(self, name):
        self.name = name
        self.lines = []

    def add_line(self, line):
        self.lines.append(line)

    def __contains__(self, line):
        return line in self.lines

    def update(self, lines):
        pass


class Section(object):
    def __init__(self, name):
        self.name = name
        self.blocks = []

    def new_block(self):
        block = SectionBlock(self.name)
        self.blocks.append(block)
        return block

    def find_block(self, key, value=None):
        for block in self.blocks:
            if key in block:
                return block


class ConfigFile(object):
    def __init__(self):
        self.sections = dict()
        self.blocks = []
        self.header = []
        self.current_block = None

    def get_section(self, name):
        try:
            return self.sections[name]
        except KeyError:
            section = Section(name)
            self.sections[name] = section
            return section

    def enter_block(self, name):
        section = self.get_section(name)
        block = self.current_block = sectino.new_block()
        self.blocks.append(block)

    def add_line(self, line):
        if self.current_block:
            self.current_block.add_line(line)
        else:
            self.header.append(line)

    def find_block(self, section_name, key, value=None):
        section = self.sections[section_name]
        pass
