import os
import unittest
from unittest.mock import MagicMock, patch

from flask import Flask
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request

from util.request import get_request_ip


class TestGetRequestIP(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def _create_request(self, remote_addr=None, headers=None):
        """Helper method to create a test request"""
        builder = EnvironBuilder(headers=headers or {})
        env = builder.get_environ()
        if remote_addr:
            env["REMOTE_ADDR"] = remote_addr
        return Request(env)

    def test_x_forwarded_for_single_ip(self):
        """Test getting IP from X-Forwarded-For with single IP"""
        headers = {"X-Forwarded-For": "203.0.113.195"}
        with patch("util.request.request", self._create_request(headers=headers)):
            self.assertEqual(get_request_ip(), "203.0.113.195")

    def test_x_forwarded_for_multiple_ips(self):
        """Test getting IP from X-Forwarded-For with multiple IPs"""
        headers = {"X-Forwarded-For": "203.0.113.195, 70.41.3.18, 150.172.238.178"}
        with patch("util.request.request", self._create_request(headers=headers)):
            # Should return first IP (client's IP)
            self.assertEqual(get_request_ip(), "203.0.113.195")

    def test_empty_x_forwarded_for(self):
        """Test with empty X-Forwarded-For header"""
        headers = {"X-Forwarded-For": ""}
        with patch(
            "util.request.request", self._create_request(remote_addr="192.168.1.1", headers=headers)
        ):
            self.assertEqual(get_request_ip(), "192.168.1.1")


if __name__ == "__main__":
    unittest.main()
