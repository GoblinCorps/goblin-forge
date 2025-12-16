#!/usr/bin/env python3
"""Tests for the command parser"""

import unittest
import sys
sys.path.insert(0, '.')

from daemon import CommandParser


class TestCommandParser(unittest.TestCase):
    """Test command parsing"""

    def setUp(self):
        self.parser = CommandParser()

    def test_spawn_simple(self):
        result = self.parser.parse("spawn coder")
        self.assertEqual(result["action"], "spawn")
        self.assertEqual(result["name"], "coder")

    def test_spawn_with_agent(self):
        result = self.parser.parse("spawn coder with agent aider")
        self.assertEqual(result["action"], "spawn")
        self.assertEqual(result["name"], "coder")
        self.assertEqual(result["agent"], "aider")

    def test_spawn_with_task(self):
        result = self.parser.parse("spawn reviewer to review the pull request")
        self.assertEqual(result["action"], "spawn")
        self.assertEqual(result["name"], "reviewer")
        self.assertIn("task", result)

    def test_attach(self):
        result = self.parser.parse("attach to goblin coder")
        self.assertEqual(result["action"], "attach")
        self.assertEqual(result["name"], "coder")

    def test_attach_short(self):
        result = self.parser.parse("attach coder")
        self.assertEqual(result["action"], "attach")
        self.assertEqual(result["name"], "coder")

    def test_stop(self):
        result = self.parser.parse("stop goblin tester")
        self.assertEqual(result["action"], "stop")
        self.assertEqual(result["name"], "tester")

    def test_kill(self):
        result = self.parser.parse("kill goblin tester")
        self.assertEqual(result["action"], "kill")
        self.assertEqual(result["name"], "tester")

    def test_list(self):
        result = self.parser.parse("list goblins")
        self.assertEqual(result["action"], "list")

    def test_list_alt(self):
        result = self.parser.parse("show all goblins")
        self.assertEqual(result["action"], "list")

    def test_status(self):
        result = self.parser.parse("show status")
        self.assertEqual(result["action"], "status")

    def test_diff(self):
        result = self.parser.parse("show diff for coder")
        self.assertEqual(result["action"], "diff")
        self.assertEqual(result["name"], "coder")

    def test_diff_natural(self):
        result = self.parser.parse("what did coder change")
        self.assertEqual(result["action"], "diff")
        self.assertEqual(result["name"], "coder")

    def test_commit(self):
        result = self.parser.parse("commit coder with message fix the bug")
        self.assertEqual(result["action"], "commit")
        self.assertEqual(result["name"], "coder")
        self.assertEqual(result["message"], "fix the bug")

    def test_push(self):
        result = self.parser.parse("push coder")
        self.assertEqual(result["action"], "push")
        self.assertEqual(result["name"], "coder")

    def test_task(self):
        result = self.parser.parse("tell coder to fix the login page")
        self.assertEqual(result["action"], "task")
        self.assertEqual(result["name"], "coder")
        self.assertEqual(result["description"], "fix the login page")

    def test_dashboard(self):
        result = self.parser.parse("open dashboard")
        self.assertEqual(result["action"], "top")

    def test_help(self):
        result = self.parser.parse("show help")
        self.assertEqual(result["action"], "help")

    def test_exit(self):
        result = self.parser.parse("exit listening")
        self.assertEqual(result["action"], "exit_voice")

    def test_unknown(self):
        result = self.parser.parse("do something random")
        self.assertEqual(result["action"], "unknown")
        self.assertIn("raw", result)

    def test_filler_words(self):
        result = self.parser.parse("um like spawn uh coder you know")
        self.assertEqual(result["action"], "spawn")
        self.assertEqual(result["name"], "coder")

    def test_case_insensitive(self):
        result = self.parser.parse("SPAWN CODER")
        self.assertEqual(result["action"], "spawn")
        self.assertEqual(result["name"], "coder")


if __name__ == "__main__":
    unittest.main()
