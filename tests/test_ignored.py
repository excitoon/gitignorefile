import os
import unittest

import gitignorefile


class TestIgnored(unittest.TestCase):
    def test_simple(self):
        self.assertFalse(gitignorefile.ignored(__file__))
        self.assertTrue(gitignorefile.ignored(f"{os.path.dirname(__file__)}/__pycache__/some.pyc"))
