"""Tests for configuration module"""

import unittest
import tempfile
import os
from pathlib import Path

from mail2printer.config import Config


class TestConfig(unittest.TestCase):
    """Test configuration functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "test_config.yaml"
    
    def tearDown(self):
        """Clean up test fixtures"""
        if self.config_path.exists():
            os.unlink(self.config_path)
        os.rmdir(self.temp_dir)
    
    def test_default_config(self):
        """Test default configuration values"""
        config = Config(str(self.config_path))
        
        # Test some default values
        self.assertEqual(config.get('email.server'), 'imap.gmail.com')
        self.assertEqual(config.get('email.port'), 993)
        self.assertTrue(config.get('email.use_ssl'))
        self.assertEqual(config.get('printer.paper_size'), 'A4')
    
    def test_config_get_set(self):
        """Test getting and setting configuration values"""
        config = Config(str(self.config_path))
        
        # Test setting values
        config.set('email.username', 'test@example.com')
        config.set('printer.name', 'TestPrinter')
        
        # Test getting values
        self.assertEqual(config.get('email.username'), 'test@example.com')
        self.assertEqual(config.get('printer.name'), 'TestPrinter')
    
    def test_config_validation(self):
        """Test configuration validation"""
        config = Config(str(self.config_path))
        
        # Should fail validation with empty username/password
        self.assertFalse(config.validate())
        
        # Should pass validation with required fields
        config.set('email.username', 'test@example.com')
        config.set('email.password', 'password123')
        self.assertTrue(config.validate())
    
    def test_config_file_creation(self):
        """Test configuration file creation"""
        config = Config(str(self.config_path))
        
        # File should be created with defaults
        self.assertTrue(self.config_path.exists())
        
        # Load again and verify
        config2 = Config(str(self.config_path))
        self.assertEqual(config.get('email.server'), config2.get('email.server'))


if __name__ == '__main__':
    unittest.main()