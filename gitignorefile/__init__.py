import collections
import os
import re


def parse(full_path, base_path=None):
    if base_path is None:
        base_path = os.path.dirname(full_path) or os.path.dirname(os.path.abspath(full_path))

    rules = []
    with open(full_path) as ignore_file:
        for i, line in enumerate(ignore_file, start=1):
            line = line.rstrip("\r\n")
            rule = _rule_from_pattern(line, source=(full_path, i))
            if rule:
                rules.append(rule)

    # TODO probably combine to single regexp.

    # We have negation rules. We can't use a simple "any" to evaluate them.
    # Later rules override earlier rules.
    return lambda file_path, is_dir=None: _handle_negation(file_path, rules, base_path=base_path, is_dir=is_dir)


def ignore():
    matches = Cache()
    return lambda root, names: {name for name in names if matches(os.path.join(root, name))}


def ignored(path, is_dir=None):
    return Cache()(path, is_dir=is_dir)


class Cache:
    def __init__(self):
        self.__gitignores = {}

    def __get_parents(self, path, is_dir):
        if not is_dir:
            path = os.path.dirname(path)
            yield path

        while True:
            new_path = os.path.dirname(path)
            if not os.path.samefile(path, new_path):
                yield new_path
                path = new_path
            else:
                break

    def __call__(self, path, is_dir=None):
        if is_dir is None:
            is_dir = os.path.isdir(path)

        add_to_children = {}
        plain_paths = []
        for parent in self.__get_parents(os.path.abspath(path), is_dir=is_dir):
            if parent in self.__gitignores:
                break

            elif os.path.isfile(os.path.join(parent, ".gitignore")):
                p = parse(os.path.join(parent, ".gitignore"), base_path=parent)
                add_to_children[parent] = (p, plain_paths)
                plain_paths = []

            else:
                plain_paths.append(parent)

        else:
            for plain_path in plain_paths:
                self.__gitignores[plain_path] = []

            if not add_to_children:
                return False

        for parent, (_, parent_plain_paths) in reversed(list(add_to_children.items())):
            self.__gitignores[parent] = []
            for parent_to_add, (gitignore_to_add, _) in reversed(list(add_to_children.items())):
                self.__gitignores[parent].append(gitignore_to_add)
                if parent_to_add == parent:
                    break

            self.__gitignores[parent].reverse()
            for plain_path in parent_plain_paths:
                self.__gitignores[plain_path] = self.__gitignores[parent]

        return any(
            (m(path, is_dir=is_dir) for m in self.__gitignores[parent])
        )  # This parent comes either from first or second loop.


def _handle_negation(file_path, rules, base_path=None, is_dir=None):
    """
    Because Git allows for nested `.gitignore` files, a `base_path` value
    is required for correct behavior.
    """
    return_immediately = not any((r.negation for r in rules))

    if is_dir is None:
        is_dir = os.path.isdir(file_path)

    if base_path is not None:
        rel_path = os.path.relpath(file_path, base_path)
    else:
        rel_path = file_path

    if rel_path.startswith(f".{os.sep}"):
        rel_path = rel_path[2:]

    matched = False
    for rule in rules:
        if rule.match(rel_path, is_dir):
            matched = not rule.negation
            if matched and return_immediately:
                return True

    else:
        return matched


def _rule_from_pattern(pattern, source=None):
    """
    Take a `.gitignore` match pattern, such as "*.py[cod]" or "**/*.bak",
    and return an `_IgnoreRule` suitable for matching against files and
    directories. Patterns which do not match files, such as comments
    and blank lines, will return `None`.
    """
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

    regexp = _fnmatch_pathname_to_regexp(pattern, directory_only)

    if anchored:
        regexp = f"^{regexp}"

    return _IgnoreRule(
        pattern=orig_pattern,
        regexp=regexp,
        negation=negation,
        directory_only=directory_only,
        anchored=anchored,
        source=source,
    )


_IGNORE_RULE_FIELDS = [
    "pattern",
    "regexp",  # Basic values
    "negation",
    "directory_only",
    "anchored",  # Behavior flags
    "source",  # (file, line) tuple for reporting
]


class _IgnoreRule(collections.namedtuple("_IgnoreRule_", _IGNORE_RULE_FIELDS)):
    def __str__(self):
        return self.pattern

    def __repr__(self):
        return "".join(["_IgnoreRule('", self.pattern, "')"])

    def match(self, rel_path, is_dir):
        match = re.search(self.regexp, rel_path)

        # If we need a directory, check there is something after slash and if there is not, target must be a directory.
        # If there is something after slash then it's a directory irrelevant to type of target.
        # `self.directory_only` implies we have group number 1.
        # N.B. Question mark inside a group without a name can shift indices. :(
        return match and (not self.directory_only or match.group(1) is not None or is_dir)


def _seps_non_sep_expr():
    if os.altsep is None:
        seps = re.escape(os.sep)
        non_sep = f"[^{re.escape(os.sep)}]"

    else:
        seps = f"[{re.escape(os.sep)}{re.escape(os.altsep)}]"
        non_sep = f"[^{re.escape(os.sep)}{re.escape(os.altsep)}]"

    return seps, non_sep


# Frustratingly, python's fnmatch doesn't provide the FNM_PATHNAME
# option that `.gitignore`'s behavior depends on.
def _fnmatch_pathname_to_regexp(pattern, directory_only):
    """
    Implements fnmatch style-behavior, as though with FNM_PATHNAME flagged;
    the path separator will not match shell-style '*' and '.' wildcards.
    """
    i, n = 0, len(pattern)

    seps_group, non_sep = _seps_non_sep_expr()
    res = [f"(?:^|{seps_group})"] if pattern else []  # Empty name means no path fragment.
    while i < n:
        c = pattern[i]
        i += 1
        if c == "*":
            try:
                if pattern[i] == "*":
                    i += 1
                    res.append(".*")
                    if pattern[i] == "/":
                        i += 1
                        res.append(f"{seps_group}?")
                else:
                    res.append(f"{non_sep}*")
            except IndexError:
                res.append(f"{non_sep}*")

        elif c == "?":
            res.append(non_sep)

        elif c == "/":
            res.append(seps_group)

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
        res.append(f"({seps_group}.+)?$")

    else:
        res.append(f"(?:{seps_group}|$)")

    return "".join(res)
