"""Tests for service module"""

import unittest
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

# Mock the problematic modules before importing the service
sys.modules['PIL'] = MagicMock()
sys.modules['PIL.Image'] = MagicMock()
sys.modules['pycups'] = MagicMock()
sys.modules['weasyprint'] = MagicMock()

from mail2printer.config import Config
from mail2printer.service import Mail2PrinterService
from mail2printer.email_handler import EmailMessage


class TestMail2PrinterService(unittest.TestCase):
    """Test Mail2PrinterService functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "test_config.yaml"
        
        # Create a minimal config
        with open(self.config_path, 'w') as f:
            f.write("""
email:
  username: test@example.com
  password: testpass
  server: imap.example.com
  port: 993
processing:
  print_attachments: true
  print_text_emails: true
  print_html_emails: true
""")
        
        self.config = Config(str(self.config_path))
        
        # Mock the dependencies that require external libraries
        with patch('mail2printer.service.EmailHandler'), \
             patch('mail2printer.service.PrinterManager'):
            self.service = Mail2PrinterService(self.config)
            
        # Mock the printer manager and email handler
        self.service.printer_manager = Mock()
        self.service.email_handler = Mock()
    
    def tearDown(self):
        """Clean up test fixtures"""
        if self.config_path.exists():
            os.unlink(self.config_path)
        os.rmdir(self.temp_dir)
    
    def _create_mock_email(self, has_attachments=False, has_text_content=False, has_html_content=False):
        """Create a mock email message"""
        email_msg = Mock(spec=EmailMessage)
        email_msg.sender = "sender@example.com"
        email_msg.subject = "Test Subject"
        
        if has_attachments:
            email_msg.attachments = [{'filename': 'test.pdf', 'data': b'test'}]
        else:
            email_msg.attachments = []
            
        email_msg.text_content = "Test text content" if has_text_content else ""
        email_msg.html_content = "<p>Test HTML content</p>" if has_html_content else ""
        
        return email_msg
    
    def test_process_email_with_attachments_only(self):
        """Test that when email has attachments, only attachments are printed"""
        # Setup
        email_msg = self._create_mock_email(has_attachments=True, has_text_content=True, has_html_content=True)
        
        # Mock the printing methods
        self.service._print_attachments = Mock(return_value=True)
        self.service._print_email_content = Mock(return_value=True)
        self.service._should_print_content = Mock(return_value=True)
        
        # Execute
        self.service._process_single_email(email_msg)
        
        # Verify
        self.service._print_attachments.assert_called_once_with(email_msg)
        self.service._print_email_content.assert_not_called()  # Should NOT be called
        self.assertEqual(self.service.stats['emails_printed'], 1)
    
    def test_process_email_without_attachments_prints_content(self):
        """Test that when email has no attachments, email content is printed"""
        # Setup
        email_msg = self._create_mock_email(has_attachments=False, has_text_content=True)
        
        # Mock the printing methods
        self.service._print_attachments = Mock(return_value=True)
        self.service._print_email_content = Mock(return_value=True)
        self.service._should_print_content = Mock(return_value=True)
        
        # Execute
        self.service._process_single_email(email_msg)
        
        # Verify
        self.service._print_attachments.assert_not_called()  # Should NOT be called
        self.service._print_email_content.assert_called_once_with(email_msg)
        self.assertEqual(self.service.stats['emails_printed'], 1)
    
    def test_process_email_without_attachments_or_content(self):
        """Test that when email has no attachments and no content, nothing is printed"""
        # Setup
        email_msg = self._create_mock_email(has_attachments=False, has_text_content=False, has_html_content=False)
        
        # Mock the printing methods
        self.service._print_attachments = Mock(return_value=True)
        self.service._print_email_content = Mock(return_value=True)
        self.service._should_print_content = Mock(return_value=False)  # No content to print
        
        # Execute
        self.service._process_single_email(email_msg)
        
        # Verify
        self.service._print_attachments.assert_not_called()
        self.service._print_email_content.assert_not_called()
        self.assertEqual(self.service.stats['emails_printed'], 0)  # Nothing printed
    
    def test_process_email_attachments_disabled_in_config(self):
        """Test behavior when attachment printing is disabled in config"""
        # Setup - disable attachment printing
        self.config.set('processing.print_attachments', False)
        email_msg = self._create_mock_email(has_attachments=True, has_text_content=True)
        
        # Mock the printing methods
        self.service._print_attachments = Mock(return_value=True)
        self.service._print_email_content = Mock(return_value=True)
        self.service._should_print_content = Mock(return_value=True)
        
        # Execute
        self.service._process_single_email(email_msg)
        
        # Verify - should print email content instead of attachments
        self.service._print_attachments.assert_not_called()
        self.service._print_email_content.assert_called_once_with(email_msg)
        self.assertEqual(self.service.stats['emails_printed'], 1)


if __name__ == '__main__':
    unittest.main()