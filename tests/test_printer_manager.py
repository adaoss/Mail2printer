"""Tests for printer manager module"""

import unittest
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

# Mock the problematic modules before importing the printer manager
sys.modules['PIL'] = MagicMock()
sys.modules['PIL.Image'] = MagicMock()
sys.modules['pycups'] = MagicMock()
sys.modules['weasyprint'] = MagicMock()

from mail2printer.config import Config
from mail2printer.printer_manager import PrinterManager


class TestPrinterManager(unittest.TestCase):
    """Test PrinterManager functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "test_config.yaml"
        
        # Create a minimal config
        with open(self.config_path, 'w') as f:
            f.write("""
printer:
  paper_size: A4
  orientation: portrait
  quality: draft
processing:
  convert_html_to_pdf: true
""")
        
        self.config = Config(str(self.config_path))
        self.printer_manager = PrinterManager(self.config)
    
    def tearDown(self):
        """Clean up test fixtures"""
        if self.config_path.exists():
            os.unlink(self.config_path)
        os.rmdir(self.temp_dir)
    
    def test_preprocess_html_removes_cid_references(self):
        """Test that CID references are properly removed from HTML"""
        html_with_cids = """
        <html>
        <body>
            <h1>Test Email</h1>
            <img src="cid:1756037F-09AD-4C50-9C41-097AB1F4FC14" alt="Embedded image">
            <img src="CID:ANOTHER-CONTENT-ID" alt="Another image">
            <a href="cid:linked-content">Embedded link</a>
            <a href="CID:UPPER-CASE">Upper case CID</a>
            <img src="http://example.com/image.jpg" alt="Normal image">
            <a href="http://example.com">Normal link</a>
        </body>
        </html>
        """
        
        processed_html = self.printer_manager._preprocess_html_for_pdf(html_with_cids)
        
        # Verify CID references are removed
        self.assertNotIn('cid:', processed_html.lower())
        
        # Verify placeholders are added
        self.assertIn('[Embedded Image]', processed_html)
        self.assertIn('[Embedded Content]', processed_html)
        
        # Verify normal URLs are preserved
        self.assertIn('http://example.com/image.jpg', processed_html)
        self.assertIn('http://example.com', processed_html)
        
        # Verify we get a data URI for images
        self.assertIn('data:image/png;base64,', processed_html)
        
        # Verify we get placeholder hrefs for links
        self.assertIn('href="#"', processed_html)
        
    def test_preprocess_html_handles_no_cid_references(self):
        """Test that HTML without CID references is unchanged"""
        normal_html = """
        <html>
        <body>
            <h1>Normal Email</h1>
            <img src="http://example.com/image.jpg" alt="Normal image">
            <a href="http://example.com">Normal link</a>
        </body>
        </html>
        """
        
        processed_html = self.printer_manager._preprocess_html_for_pdf(normal_html)
        
        # Should be identical since no CID references
        self.assertEqual(processed_html, normal_html)
    
    def test_preprocess_html_handles_edge_cases(self):
        """Test CID preprocessing handles various edge cases"""
        edge_case_html = """
        <img src='cid:single-quotes'>
        <img src="cid:double-quotes">
        <a href='cid:link-single'>Link</a>
        <a href="cid:link-double">Link</a>
        <img src="cid:with-special-chars@domain.com">
        <img src="cid:with-dashes-and-numbers-123">
        """
        
        processed_html = self.printer_manager._preprocess_html_for_pdf(edge_case_html)
        
        # All CID references should be gone
        self.assertNotIn('cid:', processed_html.lower())
        
        # Should have appropriate placeholders
        self.assertEqual(processed_html.count('[Embedded Image]'), 4)  # 4 images
        self.assertEqual(processed_html.count('[Embedded Content]'), 2)  # 2 links


if __name__ == '__main__':
    unittest.main()