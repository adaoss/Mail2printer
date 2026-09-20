"""Tests for configuration module"""

import unittest
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Mock the problematic modules before importing the config
sys.modules['PIL'] = MagicMock()
sys.modules['PIL.Image'] = MagicMock()
sys.modules['pycups'] = MagicMock()
sys.modules['weasyprint'] = MagicMock()

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

    def test_empty_config_file_uses_defaults(self):
        """Test empty config files fall back to defaults"""
        self.config_path.write_text("")

        config = Config(str(self.config_path))

        self.assertEqual(config.get('email.server'), 'imap.gmail.com')

    def test_default_config_isolated_per_instance(self):
        """Test one config instance cannot mutate future defaults"""
        first = Config(str(self.config_path))
        first.set('filters.allowed_attachments', ['.csv'])

        other_path = Path(self.temp_dir) / "other_config.yaml"
        second = Config(str(other_path))

        self.assertEqual(
            second.get('filters.allowed_attachments'),
            ['.pdf', '.txt', '.doc', '.docx', '.jpg', '.png']
        )

        if other_path.exists():
            os.unlink(other_path)

    def test_invalid_top_level_yaml_config_raises(self):
        """Test non-mapping YAML configs are rejected"""
        self.config_path.write_text("- invalid\n- config\n")

        with self.assertRaises(ValueError):
            Config(str(self.config_path))

    def test_invalid_top_level_json_config_raises(self):
        """Test non-mapping JSON configs are rejected"""
        json_path = Path(self.temp_dir) / "test_config.json"
        json_path.write_text('["invalid", "config"]')

        try:
            with self.assertRaises(ValueError):
                Config(str(json_path))
        finally:
            if json_path.exists():
                os.unlink(json_path)


if __name__ == '__main__':
    unittest.main()