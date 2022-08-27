import os
import stat
import unittest
import unittest.mock

import gitignorefile


class TestGitIgnoreCache(unittest.TestCase):
    def test_simple(self):
        class StatResult:
            def __init__(self, ino, is_file=False):
                self.st_ino = ino
                self.st_dev = 0
                self.st_mode = stat.S_IFREG if is_file else stat.S_IFDIR

        def mock_open(path):
            data = {
                "/home/vladimir/project/directory/.gitignore": ["file.txt"],
                "/home/vladimir/project/.gitignore": ["file2.txt"],
            }

            path = os.path.abspath(path).replace(os.sep, "/")
            try:
                return unittest.mock.mock_open(read_data="\n".join(data[path]))(path)

            except KeyError:
                raise FileNotFoundError()

        def mock_stat(path):
            results = {
                "/home/vladimir/project/directory/subdirectory/file.txt": StatResult(1, True),
                "/home/vladimir/project/directory/subdirectory/file2.txt": StatResult(2, True),
                "/home/vladimir/project/directory/subdirectory": StatResult(3),
                "/home/vladimir/project/directory": StatResult(4),
                "/home/vladimir/project/directory/.gitignore": StatResult(5, True),
                "/home/vladimir/project": StatResult(6),
                "/home/vladimir/project/file.txt": StatResult(7),
                "/home/vladimir/project/.gitignore": StatResult(8, True),
                "/home/vladimir": StatResult(9),
                "/home": StatResult(10),
                "/": StatResult(11),
            }

            path = os.path.abspath(path).replace(os.sep, "/")
            try:
                return results[path]

            except KeyError:
                raise FileNotFoundError()

        with unittest.mock.patch("builtins.open", mock_open):
            with unittest.mock.patch("os.stat", mock_stat):
                cache = gitignorefile.Cache()
                self.assertTrue(cache("/home/vladimir/project/directory/subdirectory/file.txt"))
                self.assertTrue(cache("/home/vladimir/project/directory/subdirectory/file2.txt"))
                self.assertFalse(cache("/home/vladimir/project/file.txt"))
