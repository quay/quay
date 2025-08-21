#!/usr/bin/env python3
"""
Unit tests for security fixes in the Quay codebase.

This module tests the HMAC signature verification fix for pickle deserialization
in the _ResumableSHAField class to prevent arbitrary code execution vulnerabilities.
"""

import base64
import hashlib
import hmac
import pickle
import unittest
from unittest.mock import patch, MagicMock

from data.fields import _ResumableSHAField


class MockHasher:
    """Mock hasher object for testing pickle serialization."""
    
    def __init__(self, value="test_data"):
        self.value = value
        self.state = "mock_state"


class TestSecurityFixes(unittest.TestCase):
    """Test cases for security vulnerability fixes."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.field = _ResumableSHAField()
        self.test_hasher = MockHasher()
        
    def test_create_hasher_signature(self):
        """Test HMAC signature creation for pickle data."""
        test_data = b"test_pickle_data"
        signature = self.field._create_hasher_signature(test_data)
        
        # Verify signature is 64 characters (32 bytes hex-encoded)
        self.assertEqual(len(signature), 64)
        self.assertIsInstance(signature, str)
        
        # Verify signature is deterministic
        signature2 = self.field._create_hasher_signature(test_data)
        self.assertEqual(signature, signature2)
        
    def test_verify_hasher_signature_valid(self):
        """Test HMAC signature verification with valid signature."""
        test_data = b"test_pickle_data"
        signature = self.field._create_hasher_signature(test_data)
        
        # Valid signature should return True
        self.assertTrue(self.field._verify_hasher_signature(test_data, signature))
        
    def test_verify_hasher_signature_invalid(self):
        """Test HMAC signature verification with invalid signature."""
        test_data = b"test_pickle_data"
        invalid_signature = "0" * 64  # Invalid signature
        
        # Invalid signature should return False
        self.assertFalse(self.field._verify_hasher_signature(test_data, invalid_signature))
        
    def test_verify_hasher_signature_tampered_data(self):
        """Test HMAC signature verification with tampered data."""
        original_data = b"test_pickle_data"
        tampered_data = b"tampered_pickle_data"
        signature = self.field._create_hasher_signature(original_data)
        
        # Tampered data with original signature should return False
        self.assertFalse(self.field._verify_hasher_signature(tampered_data, signature))
        
    def test_db_value_creates_signed_pickle(self):
        """Test that db_value creates properly signed pickle data."""
        serialized = self.field.db_value(self.test_hasher)
        
        # Should be base64-encoded string
        self.assertIsInstance(serialized, str)
        
        # Should be valid base64
        try:
            decoded = base64.b64decode(serialized.encode('ascii'))
            self.assertIsInstance(decoded, bytes)
        except Exception as e:
            self.fail(f"Failed to decode base64: {e}")
            
    @patch('data.fields.pickle.loads')
    def test_python_value_verifies_signature(self, mock_pickle_loads):
        """Test that python_value verifies HMAC signature before unpickling."""
        # Create a properly signed pickle
        test_data = pickle.dumps(self.test_hasher)
        signature = self.field._create_hasher_signature(test_data)
        signed_data = signature.encode('ascii') + b'|' + test_data
        encoded_value = base64.b64encode(signed_data).decode('ascii')
        
        mock_pickle_loads.return_value = self.test_hasher
        
        # Should successfully verify and unpickle
        result = self.field.python_value(encoded_value)
        
        # Verify pickle.loads was called (signature verification passed)
        mock_pickle_loads.assert_called_once()
        self.assertEqual(result, self.test_hasher)
        
    def test_python_value_rejects_invalid_signature(self):
        """Test that python_value rejects data with invalid signature."""
        # Create pickle with invalid signature
        test_data = pickle.dumps(self.test_hasher)
        invalid_signature = "0" * 64
        signed_data = invalid_signature.encode('ascii') + b'|' + test_data
        encoded_value = base64.b64encode(signed_data).decode('ascii')
        
        # Should raise ValueError for invalid signature
        with self.assertRaises(ValueError) as context:
            self.field.python_value(encoded_value)
            
        self.assertIn("Invalid signature", str(context.exception))
        
    def test_python_value_rejects_unsigned_data(self):
        """Test that python_value rejects legacy unsigned pickle data."""
        # Create legacy unsigned pickle (just pickle data without signature)
        test_data = pickle.dumps(self.test_hasher)
        encoded_value = base64.b64encode(test_data).decode('ascii')
        
        # Should raise ValueError for missing signature
        with self.assertRaises(ValueError) as context:
            self.field.python_value(encoded_value)
            
        self.assertIn("signature", str(context.exception).lower())
        
    def test_python_value_handles_none(self):
        """Test that python_value properly handles None values."""
        result = self.field.python_value(None)
        self.assertIsNone(result)
        
    def test_db_value_handles_none(self):
        """Test that db_value properly handles None values."""
        result = self.field.db_value(None)
        self.assertIsNone(result)
        
    def test_round_trip_serialization(self):
        """Test complete round-trip serialization with signature verification."""
        # Serialize
        serialized = self.field.db_value(self.test_hasher)
        
        # Deserialize
        deserialized = self.field.python_value(serialized)
        
        # Should get back equivalent object
        self.assertEqual(deserialized.value, self.test_hasher.value)
        self.assertEqual(deserialized.state, self.test_hasher.state)


class TestMaliciousPickleProtection(unittest.TestCase):
    """Test protection against malicious pickle payloads."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.field = _ResumableSHAField()
        
    def test_rejects_malicious_pickle_without_signature(self):
        """Test that malicious pickle without proper signature is rejected."""
        # Create a malicious pickle payload (this is just a demonstration)
        malicious_code = """
import os
os.system('echo "This would be dangerous!"')
"""
        
        # This would be a real malicious payload in practice
        malicious_pickle = pickle.dumps(compile(malicious_code, '<string>', 'exec'))
        encoded_malicious = base64.b64encode(malicious_pickle).decode('ascii')
        
        # Should be rejected due to missing/invalid signature
        with self.assertRaises(ValueError):
            self.field.python_value(encoded_malicious)


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)