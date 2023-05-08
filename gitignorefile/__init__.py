"""A spec-compliant `.gitignore` parser for Python."""

from functools import cache
import os
import re

from abc import ABC, abstractmethod
from typing import Iterator

class _BasePath(ABC):
    def __init__(self, path):
        if path is None:
            path = tuple()
        if isinstance(path, str):
            # Suppose path alwats "absolute"-like
            self.__parts = type(self)._toparts(path)
        elif isinstance(path, _BasePath):
            self.__parts = path.__parts
        else:
            self.__parts = path

    @staticmethod
    @abstractmethod # Must be innermost decorator!
    def _toparts(path: str) -> tuple[str]:
        pass
    @abstractmethod
    def isfile(self) -> bool:
        pass
    @abstractmethod
    def isdir(self) -> bool:
        pass
    @abstractmethod
    def readlines(self) -> Iterator[str]:
        pass

    @property
    def parts(self):
        return self.__parts

    def join(self, name):
        return type(self)(self.__parts + (name,))

    def relpath(self, base_path):
        if self.__parts[:len(base_path.__parts)] == base_path.__parts:
            return '/'.join(self.__parts[len(base_path.__parts):])
        else:
            return None

    def convert(self, base_from, base_to):
        if self.__parts[:len(base_from.__parts)] == base_from.__parts:
            return type(base_to)(base_to.__parts + self.__parts[len(base_from.__parts):])
        return None

    def parent(self):
        return type(self)(self.__parts[:-1])

    def parents(self, root=None):
        for i in range(len(self.__parts) - 1, 0, -1):
            parent = type(self)(self.__parts[:i])
            if (root is not None) and (parent.__parts[:len(root.__parts)] != root.__parts):
                break
            yield parent

    def __str__(self):
        if self.__parts == ('', ):
            return '/'
        return '/'.join(self.__parts)

_osSeps = [ sep for sep in [os.sep, os.altsep] if sep is not None ]
_osSepsRe = re.compile('[' + ''.join(re.escape(sep) for sep in _osSeps) + ']')
class _OSPath(_BasePath):
    @staticmethod
    #@override
    def _toparts(path: str):
        global _osSepsRe
        return tuple(_osSepsRe.split(os.path.abspath(path)))
    @cache
    #@override
    def isfile(self):
        return os.path.isfile(str(self))
    @cache
    #@override
    def isdir(self):
        return os.path.isdir(str(self))
    #@override
    def readlines(self):
        with open(str(self), 'rt', encoding='utf-8') as fp:
            yield from fp

DEFAULT_IGNORE_NAMES = [".gitignore", ".git/info/exclude"]

def parse(path: _BasePath|str, base_path=None):
    """Parses single `.gitignore` file.

    Args:
        path (str): Path to `.gitignore` file.
        base_path (str): Base path for applying ignore rules.

    Returns:
        Callable[[str], bool]: Callable which returns `True` if specified path is ignored.
            You can also pass `is_dir: bool` optional parameter if you know whether the specified path is a directory.
    """

    if isinstance(path, str):
        path = _OSPath(path) # Sensible fallback, all library calls this with a _BasePath subclass

    if base_path is None:
        base_path = path.parent()

    rules = []
    for line in path.readlines():
        line = line.rstrip("\r\n")
        rule = _rule_from_pattern(line)
        if rule:
            rules.append(rule)

    return _IgnoreRules(rules, base_path).match

class Cache:
    """Caches information about different `.gitignore` files in the directory tree.

    Allows to reduce number of queries to filesystem to mininum.
    """

    def __init__(self, ignore_names=DEFAULT_IGNORE_NAMES, ignore_root=None, _Path: type[_BasePath] = _OSPath):
        """Constructs `Cache` objects.

        Args:
            ignore_names (list[str], optional): List of names of ignore files.
        """

        self._Path = _Path
        self.__ignore_names = ignore_names
        self.__gitignores = { tuple(): [] }

        # Define ignores for out of tree
        if ignore_root is not None:
            self.__ignore_root = self._Path(ignore_root)
            oot = self.__ignore_root.parent()
            self.__gitignores[oot.parts] = []
        else:
            self.__ignore_root = None

    def __call__(self, path, is_dir=None):
        """Checks whether the specified path is ignored.

        Args:
            path (str): Path to check against ignore rules.
            is_dir (bool, optional): Set if you know whether the specified path is a directory.
        """

        path = self._Path(path)
        add_to_children = {}
        plain_paths = []
        for parent in path.parents(self.__ignore_root):
            if parent.parts in self.__gitignores:
                break

            ignore_paths = []
            for ignore_name in self.__ignore_names:
                ignore_path = parent.join(ignore_name)
                if ignore_path.isfile():
                    ignore_paths.append(ignore_path)

            if ignore_paths:
                matches = [parse(ignore_path, base_path=parent) for ignore_path in ignore_paths]
                add_to_children[parent] = (matches, plain_paths)
                plain_paths = []
            else:
                plain_paths.append(parent)
        
        else:
            parent = self._Path(tuple())  # Null path.

        for plain_path in plain_paths:
            # assert plain_path.parts not in self.__gitignores
            self.__gitignores[plain_path.parts] = self.__gitignores[parent.parts]

        for parent, (_, parent_plain_paths) in reversed(list(add_to_children.items())):
            # assert parent.parts not in self.__gitignores
            self.__gitignores[parent.parts] = self.__gitignores[parent.parts[:-1]].copy()
            for parent_to_add, (gitignores_to_add, _) in reversed(list(add_to_children.items())):
                self.__gitignores[parent.parts].extend(gitignores_to_add)
                if parent_to_add == parent:
                    break

            self.__gitignores[parent.parts].reverse()

            for plain_path in parent_plain_paths:
                # assert plain_path.parts not in self.__gitignores
                self.__gitignores[plain_path.parts] = self.__gitignores[parent.parts]

        # This parent comes either from first or second loop._Path = None # @IMPORTANT: TO BE FILLED BY IMPORTER
        return any((m(path, is_dir=is_dir) for m in self.__gitignores[parent.parts]))

def _rule_from_pattern(pattern):
    # Takes a `.gitignore` match pattern, such as "*.py[cod]" or "**/*.bak",
    # and returns an `_IgnoreRule` suitable for matching against files and
    # directories. Patterns which do not match files, such as comments
    # and blank lines, will return `None`.

    # Store the exact pattern for our repr and string functions
    orig_pattern = pattern

    # Early returns follow
    # Discard comments and separators
    if not pattern.lstrip() or pattern.lstrip().startswith("#"):
        return

    # Discard anything with more than two consecutive asterisks
    if "***" in pattern:
        return

    # Strip leading bang before examining double asterisks
    if pattern.startswith("!"):
        negation = True
        pattern = pattern[1:]
    else:
        negation = False

    # Discard anything with invalid double-asterisks -- they can appear
    # at the start or the end, or be surrounded by slashes
    for m in re.finditer("\\*\\*", pattern):
        start_index = m.start()
        if (
            start_index != 0
            and start_index != len(pattern) - 2
            and (pattern[start_index - 1] != "/" or pattern[start_index + 2] != "/")
        ):
            return

    # Special-casing '/', which doesn't match any files or directories
    if pattern.rstrip() == "/":
        return

    directory_only = pattern.endswith("/")

    # A slash is a sign that we're tied to the `base_path` of our rule
    # set.
    anchored = "/" in pattern[:-1]

    if pattern.startswith("/"):
        pattern = pattern[1:]
    if pattern.startswith("**"):
        pattern = pattern[2:]
        anchored = False
    if pattern.startswith("/"):
        pattern = pattern[1:]
    if pattern.endswith("/"):
        pattern = pattern[:-1]

    # patterns with leading hashes are escaped with a backslash in front, unescape it
    if pattern.startswith("\\#"):
        pattern = pattern[1:]

    # trailing spaces are ignored unless they are escaped with a backslash
    i = len(pattern) - 1
    striptrailingspaces = True
    while i > 1 and pattern[i] == " ":
        if pattern[i - 1] == "\\":
            pattern = pattern[: i - 1] + pattern[i:]
            i -= 1
            striptrailingspaces = False
        else:
            if striptrailingspaces:
                pattern = pattern[:i]
        i -= 1

    regexp = _fnmatch_pathname_to_regexp(pattern, anchored, directory_only)
    return _IgnoreRule(regexp, negation, directory_only)


class _IgnoreRules:
    def __init__(self, rules, base_path: _BasePath):
        self.__rules = rules
        self.__can_return_immediately = not any((r.negation for r in rules))
        self.__base_path = base_path

    def match(self, path, is_dir=None):
        if isinstance(path, str):
            path = type(self.__base_path)(path)

        rel_path = path.relpath(self.__base_path)

        if rel_path is not None:
            if is_dir is None:
                is_dir = path.isdir()  # TODO Pass callable here.

            if self.__can_return_immediately:
                return any((r.match(rel_path, is_dir) for r in self.__rules))

            else:
                matched = False
                for rule in self.__rules:
                    if rule.match(rel_path, is_dir):
                        matched = not rule.negation

                else:
                    return matched

        else:
            return False


class _IgnoreRule:
    def __init__(self, regexp, negation, directory_only):
        self.__regexp = re.compile(regexp)
        self.__negation = negation
        self.__directory_only = directory_only
        self.__match = self.__regexp.match

    @property
    def regexp(self):
        return self.__regexp

    @property
    def negation(self):
        return self.__negation

    def match(self, rel_path, is_dir):
        m = self.__match(rel_path)

        # If we need a directory, check there is something after slash and if there is not, target must be a directory.
        # If there is something after slash then it's a directory irrelevant to type of target.
        # `self.directory_only` implies we have group number 1.
        # N.B. Question mark inside a group without a name can shift indices. :(
        return m and (not self.__directory_only or m.group(1) is not None or is_dir)

def _fnmatch_pathname_to_regexp(pattern, anchored, directory_only):
    # Implements `fnmatch` style-behavior, as though with `FNM_PATHNAME` flagged;
    # the path separator will not match shell-style `*` and `.` wildcards.

    # Frustratingly, python's fnmatch doesn't provide the FNM_PATHNAME
    # option that `.gitignore`'s behavior depends on.

    if not pattern:
        if directory_only:
            return "[^/]+(/.+)?$"  # Empty name means no path fragment.

        else:
            return ".*"

    i, n = 0, len(pattern)

    res = ["(?:^|.+/)" if not anchored else ""]
    while i < n:
        c = pattern[i]
        i += 1
        if c == "*":
            if i < n and pattern[i] == "*":
                i += 1
                if i < n and pattern[i] == "/":
                    i += 1
                    res.append("(.+/)?")  # `/**/` matches `/`.

                else:
                    res.append(".*")

            else:
                res.append("[^/]*")

        elif c == "?":
            res.append("[^/]")

        elif c == "[":
            j = i
            if j < n and pattern[j] == "!":
                j += 1
            if j < n and pattern[j] == "]":
                j += 1
            while j < n and pattern[j] != "]":
                j += 1

            if j >= n:
                res.append("\\[")
            else:
                stuff = pattern[i:j].replace("\\", "\\\\")
                i = j + 1
                if stuff[0] == "!":
                    stuff = f"^{stuff[1:]}"
                elif stuff[0] == "^":
                    stuff = f"\\{stuff}"
                res.append(f"[{stuff}]")

        else:
            res.append(re.escape(c))

    if directory_only:  # In this case we are interested if there is something after slash.
        res.append("(/.+)?$")

    else:
        res.append("(?:/.+)?$")

    return "".join(res)
