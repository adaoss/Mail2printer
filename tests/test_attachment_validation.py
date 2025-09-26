"""
Test for email attachment size validation bug fix
"""

import unittest
import sys
from unittest.mock import MagicMock

# Mock the problematic modules before importing
sys.modules['PIL'] = MagicMock()
sys.modules['PIL.Image'] = MagicMock()
sys.modules['pycups'] = MagicMock()
sys.modules['weasyprint'] = MagicMock()

import email
from mail2printer.email_handler import EmailMessage


class TestAttachmentSizeValidation(unittest.TestCase):
    """Test attachment size validation fix"""
    
    def test_large_attachment_skipped(self):
        """Test that attachments exceeding size limit are skipped"""
        # Create a simple email with a large attachment
        msg = email.message.EmailMessage()
        msg['Subject'] = 'Test Email'
        msg['From'] = 'test@example.com'
        msg['To'] = 'recipient@example.com'
        
        # Add a large attachment part
        attachment_part = email.message.EmailMessage()
        attachment_part.set_content(b'x' * 20000000, maintype='application', subtype='octet-stream')  # 20MB attachment
        attachment_part['Content-Disposition'] = 'attachment; filename="large_file.txt"'
        msg.attach(attachment_part)
        
        # Create EmailMessage with 10MB limit (default)
        email_message = EmailMessage(msg, max_attachment_size=10485760)
        
        # Should have no attachments because it was too large
        self.assertEqual(len(email_message.attachments), 0)
    
    def test_small_attachment_accepted(self):
        """Test that attachments under size limit are accepted"""
        # Create a simple email with a small attachment
        msg = email.message.EmailMessage()
        msg['Subject'] = 'Test Email'
        msg['From'] = 'test@example.com'  
        msg['To'] = 'recipient@example.com'
        
        # Add a small attachment part
        attachment_part = email.message.EmailMessage()
        attachment_part.set_content(b'small content', maintype='text', subtype='plain')
        attachment_part['Content-Disposition'] = 'attachment; filename="small_file.txt"'
        msg.attach(attachment_part)
        
        # Create EmailMessage with 10MB limit (default)
        email_message = EmailMessage(msg, max_attachment_size=10485760)
        
        # Should have one attachment
        self.assertEqual(len(email_message.attachments), 1)
        self.assertEqual(email_message.attachments[0]['filename'], 'small_file.txt')


if __name__ == '__main__':
    unittest.main()