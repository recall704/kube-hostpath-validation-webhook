import unittest
from app import validate_rule

class TestApp(unittest.TestCase):
    def test_validate_rule(self):
        # - "^/root/.ssh" not allowed
        rule = r"^/root/.ssh\/?$"
        hostpath = "/root/.ssh"
        self.assertTrue(validate_rule(rule, hostpath))

        # - "^/root/.ssh" not allowed
        rule = r"^/root/.ssh\/?$"
        hostpath = "/root/.ssh/"
        self.assertTrue(validate_rule(rule, hostpath))

        # - "^/root/.ssh/211" allowed
        rule = r"^/root/.ssh\/?$"
        hostpath = "/root/.ssh/211"
        self.assertFalse(validate_rule(rule, hostpath))

        # - "^/home/(.*?)/.ssh"
        rule = r"^/home/(.*?)/.ssh\/?$"
        hostpath = "/home/username/.ssh"
        self.assertTrue(validate_rule(rule, hostpath))

if __name__ == '__main__':
    unittest.main()