import os
import sys
import tempfile
import unittest
import unittest.mock

import gitignorefile


class Tests(unittest.TestCase):
    def test_simple(self):
        matches = _parse_gitignore_string(["__pycache__/", "*.py[cod]"], fake_base_dir="/home/michael")
        self.assertFalse(matches("/home/michael/main.py"))
        self.assertTrue(matches("/home/michael/main.pyc"))
        self.assertTrue(matches("/home/michael/dir/main.pyc"))
        self.assertTrue(matches("/home/michael/__pycache__"))
        self.assertTrue(matches("/home/michael/__pycache__/"))

    def test_simple_without_trailing_slash(self):
        matches = _parse_gitignore_string(["__pycache__", "*.py[cod]"], fake_base_dir="/home/michael")
        self.assertFalse(matches("/home/michael/main.py"))
        self.assertTrue(matches("/home/michael/main.pyc"))
        self.assertTrue(matches("/home/michael/dir/main.pyc"))
        self.assertTrue(matches("/home/michael/__pycache__"))
        self.assertTrue(matches("/home/michael/__pycache__/"))

    def test_wildcard(self):
        matches = _parse_gitignore_string(["hello.*"], fake_base_dir="/home/michael")
        self.assertTrue(matches("/home/michael/hello.txt"))
        self.assertTrue(matches("/home/michael/hello.foobar/"))
        self.assertTrue(matches("/home/michael/dir/hello.txt"))
        self.assertTrue(matches("/home/michael/hello."))
        self.assertFalse(matches("/home/michael/hello"))
        self.assertFalse(matches("/home/michael/helloX"))

    def test_anchored_wildcard(self):
        matches = _parse_gitignore_string(["/hello.*"], fake_base_dir="/home/michael")
        self.assertTrue(matches("/home/michael/hello.txt"))
        self.assertTrue(matches("/home/michael/hello.c"))
        self.assertFalse(matches("/home/michael/a/hello.java"))

    def test_trailingspaces(self):
        matches = _parse_gitignore_string(
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
        matches = _parse_gitignore_string(
            ["somematch", "#realcomment", "othermatch", "\\#imnocomment"],
            fake_base_dir="/home/michael",
        )
        self.assertTrue(matches("/home/michael/somematch"))
        self.assertFalse(matches("/home/michael/#realcomment"))
        self.assertTrue(matches("/home/michael/othermatch"))
        self.assertTrue(matches("/home/michael/#imnocomment"))

    def test_ignore_directory(self):
        matches = _parse_gitignore_string([".venv/"], fake_base_dir="/home/michael")
        self.assertTrue(matches("/home/michael/.venv"))
        self.assertTrue(matches("/home/michael/.venv/folder"))
        self.assertTrue(matches("/home/michael/.venv/file.txt"))

    def test_ignore_directory_asterisk(self):
        matches = _parse_gitignore_string([".venv/*"], fake_base_dir="/home/michael")
        self.assertFalse(matches("/home/michael/.venv"))
        self.assertTrue(matches("/home/michael/.venv/folder"))
        self.assertTrue(matches("/home/michael/.venv/file.txt"))

    def test_negation(self):
        matches = _parse_gitignore_string(
            ["*.ignore", "!keep.ignore"],
            fake_base_dir="/home/michael",
        )
        self.assertTrue(matches("/home/michael/trash.ignore"))
        self.assertFalse(matches("/home/michael/keep.ignore"))
        self.assertTrue(matches("/home/michael/waste.ignore"))

    def test_double_asterisks(self):
        matches = _parse_gitignore_string(["foo/**/Bar"], fake_base_dir="/home/michael")
        self.assertTrue(matches("/home/michael/foo/hello/Bar"))
        self.assertTrue(matches("/home/michael/foo/world/Bar"))
        self.assertTrue(matches("/home/michael/foo/Bar"))

    def test_single_asterisk(self):
        matches = _parse_gitignore_string(["*"], fake_base_dir="/home/michael")
        self.assertTrue(matches("/home/michael/file.txt"))
        self.assertTrue(matches("/home/michael/directory"))
        self.assertTrue(matches("/home/michael/directory-trailing/"))

    def test_robert_simple_rules(self):
        matches = _parse_gitignore_string(["__pycache__", "*.py[cod]", ".venv/"], fake_base_dir="/home/robert")
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
        matches = _parse_gitignore_string(
            ["somematch", "#realcomment", "othermatch", "\\#imnocomment"], fake_base_dir="/home/robert"
        )
        self.assertTrue(matches("/home/robert/somematch"))
        self.assertFalse(matches("/home/robert/#realcomment"))
        self.assertTrue(matches("/home/robert/othermatch"))
        self.assertFalse(matches("/home/robert"))
        self.assertFalse(matches("/home/robert/"))
        self.assertFalse(matches("/home/robert/\\"))
        self.assertTrue(matches("/home/robert/#imnocomment"))
        # TODO test for double slashes, dots and double dots
        # TODO also test for Windows paths, mixed slashes and test for relative and unnormalized paths

    def test_robert_wildcard(self):
        matches = _parse_gitignore_string(["hello.*"], fake_base_dir="/home/robert")
        self.assertTrue(matches("/home/robert/hello.txt"))
        self.assertTrue(matches("/home/robert/hello.foobar"))
        self.assertTrue(matches("/home/robert/hello.foobar/"))
        self.assertTrue(matches("/home/robert/dir/hello.txt"))
        # self.assertFalse(matches("/home/robert/dir/shello.txt")) FIXME

        self.assertTrue(
            matches("/home/robert/dir/hello.")
        )  # FIXME On Windows there can be no files ending with a point?

        self.assertFalse(matches("/home/robert/dir/hello"))
        self.assertFalse(matches("/home/robert/dir/helloX"))

    def test_robert_anchored_wildcard(self):
        matches = _parse_gitignore_string(["/hello.*"], fake_base_dir="/home/robert")
        self.assertTrue(matches("/home/robert/hello.txt"))
        self.assertTrue(matches("/home/robert/hello.c"))
        self.assertFalse(matches("/home/robert/a/hello.java"))

    def test_robert_negation_rules(self):
        matches = _parse_gitignore_string(["*.ignore", "!keep.ignore"], fake_base_dir="/home/robert")
        self.assertTrue(matches("/home/robert/trash.ignore"))
        self.assertTrue(matches("/home/robert/whatever.ignore"))
        self.assertFalse(matches("/home/robert/keep.ignore"))
        self.assertFalse(matches("/home/robert/!keep.ignore"))

    def test_robert_match_does_not_resolve_symlinks(self):
        """Test match on files under symlinked directories
        This mimics how virtual environment sets up the .venv directory by
        symlinking to an interpreter. This test is to ensure that the symlink is
        being ignored (matched) correctly.
        """
        with tempfile.TemporaryDirectory() as d:
            matches = _parse_gitignore_string(["*.venv"], fake_base_dir=d)
            os.makedirs(f"{d}/.venv/bin")
            os.symlink(sys.executable, f"{d}/.venv/bin/python")
            self.assertTrue(matches(f"{d}/.venv"))
            self.assertTrue(matches(f"{d}/.venv/"))
            # self.assertTrue(matches(f"{d}/.venv/bin")) # FIXME
            # self.assertTrue(matches(f"{d}/.venv/bin/")) # FIXME
            # self.assertTrue(matches(f"{d}/.venv/bin/python")) # FIXME
            self.assertFalse(matches(f"{d}/.venv2"))
            self.assertFalse(matches(f"{d}/.venv2/"))
            self.assertFalse(matches(f"{d}/.venv2/bin"))
            self.assertFalse(matches(f"{d}/.venv2/bin/"))
            self.assertFalse(matches(f"{d}/.venv2/bin/python"))
            self.assertTrue(matches(f"{d}/a.venv"))
            self.assertTrue(matches(f"{d}/a.venv/"))
            # self.assertTrue(matches(f"{d}/a.venv/bin")) #FIXME
            # self.assertTrue(matches(f"{d}/a.venv/bin/")) #FIXME
            # self.assertTrue(matches(f"{d}/a.venv/bin/python")) #FIXME

    def test_robert_match_files_under_symlink(self):
        # FIXME What's going on?
        # TODO Probably test relative symlinks.
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
            matches = _parse_gitignore_string(["*.txt"], fake_base_dir=f"{d}/symlink_to_igittigitt01")

            self.assertTrue(matches(f"{d}/symlink_to_igittigitt01/file.txt"))
            self.assertFalse(matches(f"{d}/symlink_to_igittigitt01/file.png"))

            with open(f"{d}/symlink_to_igittigitt01/file.txt", "w") as f:
                pass
            with open(f"{d}/symlink_to_igittigitt01/file.png", "w") as f:
                pass
            self.assertTrue(matches(f"{d}/symlink_to_igittigitt01/file.txt"))
            self.assertFalse(matches(f"{d}/symlink_to_igittigitt01/file.png"))

    def test_robert_parse_rule_files(self):
        matches = _parse_gitignore_string(
            [
                "test__pycache__",
                "**/test__pycache__",
                "*.py[cod]",
                ".test_venv/",
                ".test_venv/**",
                ".test_venv/*",
                "!test_inverse",
            ],
            fake_base_dir="/home/robert",
        )

        files = [
            "/home/robert/test__pycache__",
            "/home/robert/test__pycache__/.test_gitignore",
            "/home/robert/test__pycache__/excluded",
            "/home/robert/test__pycache__/excluded/excluded",
            "/home/robert/test__pycache__/excluded/excluded/excluded.txt",
            "/home/robert/test__pycache__/excluded/excluded/test_inverse",
            "/home/robert/test__pycache__/some_file.txt",
            "/home/robert/test__pycache__/test",
            "/home/robert/.test_gitignore",
            "/home/robert/.test_venv",
            "/home/robert/.test_venv/some_file.txt",
            "/home/robert/not_excluded.txt",
            "/home/robert/not_excluded",
            "/home/robert/not_excluded/test__pycache__",
            "/home/robert/not_excluded/.test_gitignore",
            "/home/robert/not_excluded/excluded_not",
            "/home/robert/not_excluded/excluded_not/sub_excluded.txt",
            "/home/robert/not_excluded/excluded",
            "/home/robert/not_excluded/excluded/excluded.txt",
            "/home/robert/not_excluded/not_excluded2.txt",
            "/home/robert/not_excluded/not_excluded2",
            "/home/robert/not_excluded/not_excluded2/sub_excluded.txt",
            "/home/robert/not_excluded/excluded_not.txt",
            "/home/robert/.test_gitignore_empty",
        ]

        filtered_names = []
        filtered_paths = []
        for path in files:
            if not matches(path):
                filtered_paths.append(path)

        return  # FIXME
        self.assertEqual(
            sorted(filtered_paths),
            [
                "/home/robert/.test_gitignore",
                "/home/robert/.test_gitignore_empty",
                "/home/robert/not_excluded",
                "/home/robert/not_excluded.txt",
                "/home/robert/not_excluded/.test_gitignore",
                "/home/robert/not_excluded/excluded",
                "/home/robert/not_excluded/excluded/excluded.txt",
                "/home/robert/not_excluded/excluded_not",
                "/home/robert/not_excluded/excluded_not.txt",
                "/home/robert/not_excluded/excluded_not/sub_excluded.txt",
                "/home/robert/not_excluded/not_excluded2",
                "/home/robert/not_excluded/not_excluded2.txt",
                "/home/robert/not_excluded/not_excluded2/sub_excluded.txt",
            ],
        )

    def test_robert_shutil_ignore_function(self):
        """
        >>> test_shutil_ignore_function()
        """
        return  # FIXME
        # Setup
        path_test_dir = pathlib.Path(__file__).parent.resolve()

        path_source_dir = path_test_dir / "example"
        path_target_dir = path_test_dir / "target"
        shutil.rmtree(path_target_dir, ignore_errors=True)

        # Test
        ignore_parser = igittigitt.IgnoreParser()
        ignore_parser.parse_rule_files(base_dir=path_source_dir, filename=".test_gitignore")
        shutil.copytree(
            path_source_dir,
            path_target_dir,
            ignore=ignore_parser.shutil_ignore,
        )

        assert len(list(path_target_dir.glob("**/*"))) == 9

        # Teardown
        shutil.rmtree(path_target_dir, ignore_errors=True)


def _parse_gitignore_string(data, fake_base_dir):
    with unittest.mock.patch("builtins.open", unittest.mock.mock_open(read_data="\n".join(data))):
        return gitignorefile.parse(f"{fake_base_dir}/.gitignore", fake_base_dir)
