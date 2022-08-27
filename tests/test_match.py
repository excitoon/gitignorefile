import os
import sys
import tempfile
import unittest
import unittest.mock

import gitignorefile


class TestMatch(unittest.TestCase):
    def test_simple(self):
        matches = self.__parse_gitignore_string(["__pycache__/", "*.py[cod]"], fake_base_dir="/home/michael")
        self.assertFalse(matches("/home/michael/main.py"))
        self.assertTrue(matches("/home/michael/main.pyc"))
        self.assertTrue(matches("/home/michael/dir/main.pyc"))
        self.assertTrue(matches("/home/michael/__pycache__"))
        self.assertTrue(matches("/home/michael/__pycache__/"))

    def test_simple_without_trailing_slash(self):
        matches = self.__parse_gitignore_string(["__pycache__", "*.py[cod]"], fake_base_dir="/home/michael")
        self.assertFalse(matches("/home/michael/main.py"))
        self.assertTrue(matches("/home/michael/main.pyc"))
        self.assertTrue(matches("/home/michael/dir/main.pyc"))
        self.assertTrue(matches("/home/michael/__pycache__"))
        self.assertTrue(matches("/home/michael/__pycache__/"))

    def test_wildcard(self):
        matches = self.__parse_gitignore_string(["hello.*"], fake_base_dir="/home/michael")
        self.assertTrue(matches("/home/michael/hello.txt"))
        self.assertTrue(matches("/home/michael/hello.foobar/"))
        self.assertTrue(matches("/home/michael/dir/hello.txt"))
        self.assertTrue(matches("/home/michael/hello."))
        self.assertFalse(matches("/home/michael/hello"))
        self.assertFalse(matches("/home/michael/helloX"))

    def test_anchored_wildcard(self):
        matches = self.__parse_gitignore_string(["/hello.*"], fake_base_dir="/home/michael")
        self.assertTrue(matches("/home/michael/hello.txt"))
        self.assertTrue(matches("/home/michael/hello.c"))
        self.assertFalse(matches("/home/michael/a/hello.java"))

    def test_trailingspaces(self):
        matches = self.__parse_gitignore_string(
            [
                "ignoretrailingspace ",
                "notignoredspace\\ ",
                "partiallyignoredspace\\  ",
                "partiallyignoredspace2 \\  ",
                "notignoredmultiplespace\\ \\ \\ ",
            ],
            fake_base_dir="/home/michael",
        )
        self.assertTrue(matches("/home/michael/ignoretrailingspace"))
        self.assertFalse(matches("/home/michael/ignoretrailingspace "))
        self.assertTrue(matches("/home/michael/partiallyignoredspace "))
        self.assertFalse(matches("/home/michael/partiallyignoredspace  "))
        self.assertFalse(matches("/home/michael/partiallyignoredspace"))
        self.assertTrue(matches("/home/michael/partiallyignoredspace2  "))
        self.assertFalse(matches("/home/michael/partiallyignoredspace2   "))
        self.assertFalse(matches("/home/michael/partiallyignoredspace2 "))
        self.assertFalse(matches("/home/michael/partiallyignoredspace2"))
        self.assertTrue(matches("/home/michael/notignoredspace "))
        self.assertFalse(matches("/home/michael/notignoredspace"))
        self.assertTrue(matches("/home/michael/notignoredmultiplespace   "))
        self.assertFalse(matches("/home/michael/notignoredmultiplespace"))

    def test_comment(self):
        matches = self.__parse_gitignore_string(
            ["somematch", "#realcomment", "othermatch", "\\#imnocomment"],
            fake_base_dir="/home/michael",
        )
        self.assertTrue(matches("/home/michael/somematch"))
        self.assertFalse(matches("/home/michael/#realcomment"))
        self.assertTrue(matches("/home/michael/othermatch"))
        self.assertTrue(matches("/home/michael/#imnocomment"))

    def test_ignore_directory(self):
        matches = self.__parse_gitignore_string([".venv/"], fake_base_dir="/home/michael")
        self.assertTrue(matches("/home/michael/.venv"))
        self.assertTrue(matches("/home/michael/.venv/folder"))
        self.assertTrue(matches("/home/michael/.venv/file.txt"))

    def test_ignore_directory_asterisk(self):
        matches = self.__parse_gitignore_string([".venv/*"], fake_base_dir="/home/michael")
        self.assertFalse(matches("/home/michael/.venv"))
        self.assertTrue(matches("/home/michael/.venv/folder"))
        self.assertTrue(matches("/home/michael/.venv/file.txt"))

    def test_negation(self):
        matches = self.__parse_gitignore_string(
            ["*.ignore", "!keep.ignore"],
            fake_base_dir="/home/michael",
        )
        self.assertTrue(matches("/home/michael/trash.ignore"))
        self.assertFalse(matches("/home/michael/keep.ignore"))
        self.assertTrue(matches("/home/michael/waste.ignore"))

    def test_double_asterisks(self):
        matches = self.__parse_gitignore_string(["foo/**/Bar"], fake_base_dir="/home/michael")
        self.assertTrue(matches("/home/michael/foo/hello/Bar"))
        self.assertTrue(matches("/home/michael/foo/world/Bar"))
        self.assertTrue(matches("/home/michael/foo/Bar"))

    def test_single_asterisk(self):
        matches = self.__parse_gitignore_string(["*"], fake_base_dir="/home/michael")
        self.assertTrue(matches("/home/michael/file.txt"))
        self.assertTrue(matches("/home/michael/directory"))
        self.assertTrue(matches("/home/michael/directory-trailing/"))

    def test_spurious_matches(self):
        matches = self.__parse_gitignore_string(["abc"], fake_base_dir="/home/michael")
        self.assertFalse(matches("/home/michael/abc.txt"))
        self.assertFalse(matches("/home/michael/file-abc.txt"))
        self.assertFalse(matches("/home/michael/fileabc"))
        self.assertFalse(matches("/home/michael/directoryabc/"))
        self.assertFalse(matches("/home/michael/directoryabc-trailing"))
        self.assertFalse(matches("/home/michael/directoryabc-trailing/"))
        self.assertFalse(matches("/home/michael/abc-suffixed/file.txt"))
        self.assertFalse(matches("/home/michael/subdir/abc.txt"))
        self.assertFalse(matches("/home/michael/subdir/directoryabc"))
        self.assertFalse(matches("/home/michael/subdir/directory-abc-trailing/"))
        self.assertFalse(matches("/home/michael/subdir/directory-abc-trailing/file.txt"))

    def test_does_not_fail_with_symlinks(self):
        with tempfile.TemporaryDirectory() as d:
            matches = self.__parse_gitignore_string(["*.venv"], fake_base_dir=d)
            os.makedirs(f"{d}/.venv/bin")
            os.symlink(sys.executable, f"{d}/.venv/bin/python")
            matches(f"{d}/.venv/bin/python")

    def test_single_letter(self):
        matches = self.__parse_gitignore_string(["a"], fake_base_dir="/home/michael")
        self.assertTrue(matches("/home/michael/a"))
        self.assertFalse(matches("/home/michael/b"))
        self.assertTrue(matches("/home/michael/b/a"))
        self.assertTrue(matches("/home/michael/a/b"))

    def test_robert_simple_rules(self):
        matches = self.__parse_gitignore_string(["__pycache__", "*.py[cod]", ".venv/"], fake_base_dir="/home/robert")
        self.assertFalse(matches("/home/robert/main.py"))
        self.assertTrue(matches("/home/robert/dir/main.pyc"))
        self.assertTrue(matches("/home/robert/__pycache__"))
        self.assertTrue(matches("/home/robert/.venv"))
        self.assertTrue(matches("/home/robert/.venv/"))
        self.assertTrue(matches("/home/robert/.venv/folder"))
        self.assertTrue(matches("/home/robert/.venv/file.txt"))
        self.assertTrue(matches("/home/robert/.venv/folder/file.txt"))
        self.assertTrue(matches("/home/robert/.venv/folder/folder"))
        self.assertTrue(matches("/home/robert/.venv/folder/folder/"))

    def test_robert_comments(self):
        matches = self.__parse_gitignore_string(
            ["somematch", "#realcomment", "othermatch", "\\#imnocomment"], fake_base_dir="/home/robert"
        )
        self.assertTrue(matches("/home/robert/somematch"))
        self.assertFalse(matches("/home/robert/#realcomment"))
        self.assertTrue(matches("/home/robert/othermatch"))
        self.assertFalse(matches("/home/robert"))
        self.assertFalse(matches("/home/robert/"))
        self.assertFalse(matches("/home/robert/\\"))
        self.assertTrue(matches("/home/robert/#imnocomment"))

    def test_robert_wildcard(self):
        matches = self.__parse_gitignore_string(["hello.*"], fake_base_dir="/home/robert")
        self.assertTrue(matches("/home/robert/hello.txt"))
        self.assertTrue(matches("/home/robert/hello.foobar"))
        self.assertTrue(matches("/home/robert/hello.foobar/"))
        self.assertTrue(matches("/home/robert/dir/hello.txt"))
        self.assertFalse(matches("/home/robert/dir/shello.txt"))

        self.assertTrue(
            matches("/home/robert/dir/hello.")
        )  # FIXME On Windows there can be no files ending with a point?

        self.assertFalse(matches("/home/robert/dir/hello"))
        self.assertFalse(matches("/home/robert/dir/helloX"))

    def test_robert_anchored_wildcard(self):
        matches = self.__parse_gitignore_string(["/hello.*"], fake_base_dir="/home/robert")
        self.assertTrue(matches("/home/robert/hello.txt"))
        self.assertTrue(matches("/home/robert/hello.c"))
        self.assertFalse(matches("/home/robert/a/hello.java"))

    def test_robert_negation_rules(self):
        matches = self.__parse_gitignore_string(["*.ignore", "!keep.ignore"], fake_base_dir="/home/robert")
        self.assertTrue(matches("/home/robert/trash.ignore"))
        self.assertTrue(matches("/home/robert/whatever.ignore"))
        self.assertFalse(matches("/home/robert/keep.ignore"))
        self.assertTrue(matches("/home/robert/!keep.ignore"))

    def test_robert_match_does_not_resolve_symlinks(self):
        """Test match on files under symlinked directories
        This mimics how virtual environment sets up the .venv directory by
        symlinking to an interpreter. This test is to ensure that the symlink is
        being ignored (matched) correctly.
        """
        with tempfile.TemporaryDirectory() as d:
            matches = self.__parse_gitignore_string(["*.venv"], fake_base_dir=d)
            os.makedirs(f"{d}/.venv/bin")
            os.symlink(sys.executable, f"{d}/.venv/bin/python")
            self.assertTrue(matches(f"{d}/.venv"))
            self.assertTrue(matches(f"{d}/.venv/"))
            self.assertTrue(matches(f"{d}/.venv/bin"))
            self.assertTrue(matches(f"{d}/.venv/bin/"))
            self.assertTrue(matches(f"{d}/.venv/bin/python"))
            self.assertFalse(matches(f"{d}/.venv2"))
            self.assertFalse(matches(f"{d}/.venv2/"))
            self.assertFalse(matches(f"{d}/.venv2/bin"))
            self.assertFalse(matches(f"{d}/.venv2/bin/"))
            self.assertFalse(matches(f"{d}/.venv2/bin/python"))
            self.assertTrue(matches(f"{d}/a.venv"))
            self.assertTrue(matches(f"{d}/a.venv/"))
            self.assertTrue(matches(f"{d}/a.venv/bin"))
            self.assertTrue(matches(f"{d}/a.venv/bin/"))
            self.assertTrue(matches(f"{d}/a.venv/bin/python"))

    def test_robert_match_files_under_symlink(self):
        # FIXME What's going on?
        """
        see: https://git-scm.com/docs/gitignore#_pattern_format
        The pattern foo/ will match a directory foo and paths underneath it,
        but will not match a regular file or a symbolic link foo
        (this is consistent with the way how pathspec works in general in Git)
        """
        pass

    def test_robert_handle_base_directories_with_a_symlink_in_their_components(self):
        """
        see https://github.com/bitranox/igittigitt/issues/28
        """
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(f"{d}/igittigitt01")
            os.symlink(f"{d}/igittigitt01", f"{d}/symlink_to_igittigitt01", target_is_directory=True)
            matches = self.__parse_gitignore_string(["*.txt"], fake_base_dir=f"{d}/symlink_to_igittigitt01")

            self.assertTrue(matches(f"{d}/symlink_to_igittigitt01/file.txt"))
            self.assertFalse(matches(f"{d}/symlink_to_igittigitt01/file.png"))

            with open(f"{d}/symlink_to_igittigitt01/file.txt", "w"):
                pass
            with open(f"{d}/symlink_to_igittigitt01/file.png", "w"):
                pass
            self.assertTrue(matches(f"{d}/symlink_to_igittigitt01/file.txt"))
            self.assertFalse(matches(f"{d}/symlink_to_igittigitt01/file.png"))

    def test_robert_parse_rule_files(self):
        matches = self.__parse_gitignore_string(
            [
                "test__pycache__",
                "*.py[cod]",
                ".test_venv/",
                ".test_venv/**",
                ".test_venv/*",
                "!test_inverse",
            ],
            fake_base_dir="/home/robert",
        )

        self.assertTrue(matches("/home/robert/test__pycache__"))
        self.assertTrue(matches("/home/robert/test__pycache__/.test_gitignore"))
        self.assertTrue(matches("/home/robert/test__pycache__/excluded"))
        self.assertTrue(matches("/home/robert/test__pycache__/excluded/excluded"))
        self.assertTrue(matches("/home/robert/test__pycache__/excluded/excluded/excluded.txt"))
        self.assertFalse(
            matches("/home/robert/test__pycache__/excluded/excluded/test_inverse")
        )  # FIXME This file would be actually ignored. :(
        self.assertTrue(matches("/home/robert/test__pycache__/some_file.txt"))
        self.assertTrue(matches("/home/robert/test__pycache__/test"))
        self.assertFalse(matches("/home/robert/.test_gitignore"))
        self.assertTrue(matches("/home/robert/.test_venv"))
        self.assertTrue(matches("/home/robert/.test_venv/some_file.txt"))
        self.assertFalse(matches("/home/robert/not_excluded.txt"))
        self.assertFalse(matches("/home/robert/not_excluded"))
        self.assertTrue(matches("/home/robert/not_excluded/test__pycache__"))
        self.assertFalse(matches("/home/robert/not_excluded/.test_gitignore"))
        self.assertFalse(matches("/home/robert/not_excluded/excluded_not"))
        self.assertFalse(matches("/home/robert/not_excluded/excluded_not/sub_excluded.txt"))
        self.assertFalse(matches("/home/robert/not_excluded/excluded"))
        self.assertFalse(matches("/home/robert/not_excluded/excluded/excluded.txt"))
        self.assertFalse(matches("/home/robert/not_excluded/not_excluded2.txt"))
        self.assertFalse(matches("/home/robert/not_excluded/not_excluded2"))
        self.assertFalse(matches("/home/robert/not_excluded/not_excluded2/sub_excluded.txt"))
        self.assertFalse(matches("/home/robert/not_excluded/excluded_not.txt"))
        self.assertFalse(matches("/home/robert/.test_gitignore_empty"))

    def __parse_gitignore_string(self, data, fake_base_dir):
        with unittest.mock.patch("builtins.open", unittest.mock.mock_open(read_data="\n".join(data))):
            return gitignorefile.parse(f"{fake_base_dir}/.gitignore", fake_base_dir)
