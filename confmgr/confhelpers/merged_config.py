# coding: utf-8
# Copyright (c) 2010-2012 Raphaël Barrois


from __future__ import unicode_literals


"""Merge configuration options from a configuration file and CLI arguments."""


class Default(object):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return 'Default(%r)' % self.value

    def __hash__(self):
        return hash(self.value)

    def __nonzero__(self):
        return bool(self.value)

    def __bool__(self):
        return bool(self.value)

    def __eq__(self, other):
        if not isinstance(other, Default):
            return NotImplemented
        return self.value == other.value


class NoDefault(object):
    pass


def normalize_key(key):
    """Normalize a config key.

    Returns the same key, with only lower-case characters and no '-'.
    """
    return key.lower().replace('-', '_')


class NormalizedDict(dict):
    """A dict whose lookups are performed on normalized keys."""

    def __init__(self, *args, **kwargs):
        d = dict(*args, **kwargs)
        super(NormalizedDict, self).__init__(
            (normalize_key(k), v) for k, v in d.items())

    def __getitem__(self, key):
        return super(NormalizedDict, self).__getitem__(normalize_key(key))

    def __setitem__(self, key, value):
        self[normalize_key(key)] = value


class DictNamespace(object):
    """Convert a 'Namespace' into a dict-like object."""

    def __init__(self, ns):
        self.ns = ns

    def get(self, key, default=NoDefault):
        try:
            return self[key]
        except KeyError:
            if default is NoDefault:
                raise
            return default

    def __getitem__(self, key):
        key = normalize_key(key)
        try:
            return getattr(self.ns, key)
        except AttributeError as e:
            raise KeyError(str(e))

    def __hash__(self):
        return hash((self.__class__, self.ns))

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.ns)


class MergedConfig(object):
    """A merged configuration holder.

    Merges options from a set of dicts."""

    def __init__(self, *options):
        self.options = []
        for option in options:
            self.add_options(option)

    def add_options(self, options):
        self.options.append(options)

    def get(self, key, default=NoDefault):
        """Retrieve a value from its key.

        Retrieval steps are:
        1) Normalize the key
        2) For each option group:
           a) Retrieve the value at that key
           b) If no value exists, continue
           c) If the value is an instance of 'Default', continue
           d) Otherwise, return the value
        3) If no option had a non-default value for the key, return the
            first Default() option for the key (or :arg:`default`).
        """
        key = normalize_key(key)
        if default is NoDefault:
            defaults = []
        else:
            defaults = [default]

        for options in self.options:
            try:
                value = options[key]
            except KeyError:
                continue

            if isinstance(value, Default):
                defaults.append(value.value)
                continue
            else:
                return value

        return defaults[0]

    def get_tuple(self, key, default=(), separator=' '):
        value = self.get(key, default)
        if isinstance(value, basestring):
            value = value.split(separator)
        return tuple(value)

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.options)

    def __hash__(self):
        return hash((self.__class__, self.options))
