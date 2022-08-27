import collections
import os
import re


def parse(full_path, base_dir=None):
    if base_dir is None:
        base_dir = os.path.dirname(full_path)

    rules = []
    with open(full_path) as ignore_file:
        for i, line in enumerate(ignore_file, start=1):
            line = line.rstrip("\r\n")
            rule = _rule_from_pattern(line, base_path=os.path.abspath(base_dir), source=(full_path, i))
            if rule:
                rules.append(rule)

    if not any((r.negation for r in rules)):
        return lambda file_path: any((r.match(file_path) for r in rules))

    else:
        # We have negation rules. We can't use a simple "any" to evaluate them.
        # Later rules override earlier rules.
        return lambda file_path: _handle_negation(file_path, rules)


def ignore():
    matches = Cache()
    return lambda root, names: {name for name in names if matches(os.path.join(root, name))}


def ignored(path):
    return Cache()(path)


class Cache:
    def __init__(self):
        self.__gitignores = {}

    def __get_parents(self, path):
        if not os.path.isdir(path):
            path = os.path.dirname(path)
            yield path

        while True:
            new_path = os.path.dirname(path)
            if not os.path.samefile(path, new_path):
                yield new_path
                path = new_path
            else:
                break

    def __call__(self, path):
        add_to_children = {}
        plain_paths = []
        for parent in self.__get_parents(os.path.abspath(path)):
            if parent in self.__gitignores:
                break

            elif os.path.isfile(os.path.join(parent, ".gitignore")):
                p = parse(os.path.join(parent, ".gitignore"), base_dir=parent)
                add_to_children[parent] = (p, plain_paths)
                plain_paths = []

            else:
                plain_paths.append(parent)

        else:
            for plain_path in plain_paths:
                self.__gitignores[plain_path] = []

            if not add_to_children:
                return False

        for parent, (_, parent_plain_paths) in reversed(add_to_children.items()):
            self.__gitignores[parent] = []
            for parent_to_add, (gitignore_to_add, _) in reversed(add_to_children.items()):
                self.__gitignores[parent].append(gitignore_to_add)
                if parent_to_add == parent:
                    break

            self.__gitignores[parent].reverse()
            for plain_path in parent_plain_paths:
                self.__gitignores[plain_path] = self.__gitignores[parent]

        return any((m(path) for m in self.__gitignores[parent]))  # This parent comes either from first or second loop.


def _handle_negation(file_path, rules):
    matched = False
    for rule in rules:
        if rule.match(file_path):
            if rule.negation:
                matched = False
            else:
                matched = True
    return matched


def _rule_from_pattern(pattern, base_path=None, source=None):
    """
    Take a .gitignore match pattern, such as "*.py[cod]" or "**/*.bak",
    and return an _IgnoreRule suitable for matching against files and
    directories. Patterns which do not match files, such as comments
    and blank lines, will return None.
    Because git allows for nested .gitignore files, a base_path value
    is required for correct behavior. The base path should be absolute.
    """
    if base_path and base_path != os.path.abspath(base_path):
        raise ValueError("base_path must be absolute")
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
    if pattern[0] == "!":
        negation = True
        pattern = pattern[1:]
    else:
        negation = False
    # Discard anything with invalid double-asterisks -- they can appear
    # at the start or the end, or be surrounded by slashes
    for m in re.finditer(r"\*\*", pattern):
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
    # A slash is a sign that we're tied to the base_path of our rule
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
    regex = _fnmatch_pathname_to_regex(pattern, directory_only)
    if anchored:
        regex = f"^{regex}"
    return _IgnoreRule(
        pattern=orig_pattern,
        regex=regex,
        negation=negation,
        directory_only=directory_only,
        anchored=anchored,
        base_path=base_path,
        source=source,
    )


_IGNORE_RULE_FIELDS = [
    "pattern",
    "regex",  # Basic values
    "negation",
    "directory_only",
    "anchored",  # Behavior flags
    "base_path",  # Meaningful for gitignore-style behavior
    "source",  # (file, line) tuple for reporting
]


class _IgnoreRule(collections.namedtuple("_IgnoreRule_", _IGNORE_RULE_FIELDS)):
    def __str__(self):
        return self.pattern

    def __repr__(self):
        return "".join(["_IgnoreRule('", self.pattern, "')"])

    def match(self, abs_path):
        matched = False
        if self.base_path:
            rel_path = str(os.path.relpath(abs_path, self.base_path))
        else:
            rel_path = str(abs_path)
        seps_group, _ = _seps_non_sep_expr()
        if rel_path.startswith(f".{seps_group}"):
            rel_path = rel_path[2:]
        if re.search(self.regex, rel_path):
            matched = True
        return matched


def _seps_non_sep_expr():
    seps = [re.escape(os.sep)]
    if os.altsep is not None:
        seps.append(re.escape(os.altsep))
    return "[" + "|".join(seps) + "]", "[^{}]".format("|".join(seps))


# Frustratingly, python's fnmatch doesn't provide the FNM_PATHNAME
# option that `.gitignore`'s behavior depends on.
def _fnmatch_pathname_to_regex(pattern, directory_only):
    """
    Implements fnmatch style-behavior, as though with FNM_PATHNAME flagged;
    the path separator will not match shell-style '*' and '.' wildcards.
    """
    i, n = 0, len(pattern)

    seps_group, nonsep = _seps_non_sep_expr()
    res = [f"(^|{seps_group})"]
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
                    res.append(f"{nonsep}*")
            except IndexError:
                res.append(f"{nonsep}*")
        elif c == "?":
            res.append(nonsep)
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
                    stuff = "".join(["^", stuff[1:]])
                elif stuff[0] == "^":
                    stuff = "".join("\\" + stuff)
                res.append("[{}]".format(stuff))
        else:
            res.append(re.escape(c))
    if not directory_only:
        res.append(f"({seps_group}|$)")
    return "".join(res)
