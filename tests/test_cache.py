import os
import stat
import tempfile
import unittest
import unittest.mock

import gitignorefile


class TestCache(unittest.TestCase):
    def test_simple(self):
        class StatResult:
            def __init__(self, is_file=False):
                self.st_ino = id(self)
                self.st_dev = 0
                self.st_mode = stat.S_IFREG if is_file else stat.S_IFDIR

        class Stat:
            def __init__(self, directories, files):
                self.__filesystem = {}
                for path in directories:
                    self.__filesystem[path] = StatResult()
                for path in files:
                    self.__filesystem[path] = StatResult(True)

            def __call__(self, path):
                try:
                    return self.__filesystem[path]

                except KeyError:
                    raise FileNotFoundError()

        my_stat = Stat(
            [
                "/home/vladimir/project/directory/subdirectory",
                "/home/vladimir/project/directory",
                "/home/vladimir/project",
                "/home/vladimir",
                "/home",
                "/",
            ],
            [
                "/home/vladimir/project/directory/subdirectory/file.txt",
                "/home/vladimir/project/directory/subdirectory/file2.txt",
                "/home/vladimir/project/directory/.gitignore",
                "/home/vladimir/project/file.txt",
                "/home/vladimir/project/.gitignore",
            ],
        )

        statistics = {"open": 0, "stat": 0}

        def mock_open(path):
            data = {
                "/home/vladimir/project/directory/.gitignore": ["file.txt"],
                "/home/vladimir/project/.gitignore": ["file2.txt"],
            }

            statistics["open"] += 1
            path = os.path.abspath(path).replace(os.sep, "/")
            try:
                return unittest.mock.mock_open(read_data="\n".join(data[path]))(path)

            except KeyError:
                raise FileNotFoundError()

        def mock_stat(path):
            statistics["stat"] += 1
            path = os.path.abspath(path).replace(os.sep, "/")
            return my_stat(path)

        with unittest.mock.patch("builtins.open", mock_open):
            with unittest.mock.patch("os.stat", mock_stat):
                cache = gitignorefile.Cache()
                self.assertTrue(cache("/home/vladimir/project/directory/subdirectory/file.txt"))
                self.assertTrue(cache("/home/vladimir/project/directory/subdirectory/file2.txt"))
                self.assertTrue(cache("/home/vladimir/project/directory/file.txt"))
                self.assertTrue(cache("/home/vladimir/project/directory/file2.txt"))
                self.assertFalse(cache("/home/vladimir/project/file.txt"))

        self.assertEqual(statistics["open"], 2)
        self.assertEqual(statistics["stat"], 6 * (2 + 1) + 5)

    def test_wrong_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            matches = gitignorefile.Cache()
            os.makedirs(f"{d}/.venv/bin")
            os.symlink(f"/nonexistent-path-{id(self)}", f"{d}/.venv/bin/python")
            self.assertFalse(matches(f"{d}/.venv/bin/python"))
