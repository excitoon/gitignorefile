import os
import unittest

import gitignorefile


class TestIgnored(unittest.TestCase):
    def test_simple(self):
        for is_dir in (None, False, True):
            with self.subTest(i=is_dir):
                self.assertFalse(gitignorefile.ignored(__file__, is_dir=is_dir))
                if is_dir is not True:
                    self.assertTrue(
                        gitignorefile.ignored(f"{os.path.dirname(__file__)}/__pycache__/some.pyc", is_dir=is_dir)
                    )
                self.assertFalse(gitignorefile.ignored(os.path.dirname(__file__), is_dir=is_dir))
                if is_dir is not False:
                    self.assertTrue(gitignorefile.ignored(f"{os.path.dirname(__file__)}/__pycache__", is_dir=is_dir))
                else:
                    self.assertFalse(gitignorefile.ignored(f"{os.path.dirname(__file__)}/__pycache__", is_dir=is_dir))
