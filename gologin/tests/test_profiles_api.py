import unittest

from gologin import GoLogin

class Test(unittest.TestCase):

    def test_pass(self):
        self.assertEqual(1, 1)

    # def test_pass(self):
    #     self.assertEqual(3, 3)

if __name__ == "__main__":
    unittest.main()