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
    
    @patch('time.sleep')
    @patch('time.time')
    def test_wait_for_job_completion_success(self, mock_time, mock_sleep):
        """Test that job completion wait returns True when job completes"""
        # Mock time progression
        mock_time.side_effect = [0, 1, 2, 3]  # Simulate time passing
        
        # Mock CUPS connection with a job that completes
        mock_cups = MagicMock()
        self.printer_manager.cups_connection = mock_cups
        
        # First call: job in queue, second call: job completed (not in queue)
        mock_cups.getJobs.side_effect = [
            {123: {'job-state': 5}},  # processing
            {}  # completed (no longer in queue)
        ]
        
        # Enable waiting
        self.config.set('printer.wait_for_completion', True)
        self.config.set('printer.job_timeout', 10)
        
        result = self.printer_manager._wait_for_job_completion(123)
        
        # Should succeed
        self.assertTrue(result)
        
        # Should have checked job status
        self.assertEqual(mock_cups.getJobs.call_count, 2)
    
    @patch('time.sleep')
    @patch('time.time')
    def test_wait_for_job_completion_timeout(self, mock_time, mock_sleep):
        """Test that job completion wait returns False on timeout"""
        # Mock time progression to exceed timeout
        # Need more values for all time.time() calls including in logging
        mock_time.side_effect = [0, 5, 11, 11, 11, 11, 11, 11]  # Exceed 10s timeout
        
        # Mock CUPS connection with a job that never completes
        mock_cups = MagicMock()
        self.printer_manager.cups_connection = mock_cups
        mock_cups.getJobs.return_value = {123: {'job-state': 5}}  # Always processing
        
        # Enable waiting with short timeout
        self.config.set('printer.wait_for_completion', True)
        self.config.set('printer.job_timeout', 10)
        
        result = self.printer_manager._wait_for_job_completion(123)
        
        # Should timeout and return False
        self.assertFalse(result)
    
    def test_wait_for_job_completion_disabled(self):
        """Test that job completion wait returns immediately when disabled"""
        # Disable waiting
        self.config.set('printer.wait_for_completion', False)
        
        result = self.printer_manager._wait_for_job_completion(123)
        
        # Should return True immediately without checking status
        self.assertTrue(result)
    
    @patch('time.sleep')
    @patch('time.time')
    def test_wait_for_job_completion_job_failed(self, mock_time, mock_sleep):
        """Test that job completion wait detects failed jobs"""
        # Mock time progression
        mock_time.side_effect = [0, 1, 2]
        
        # Mock CUPS connection with a job that fails
        mock_cups = MagicMock()
        self.printer_manager.cups_connection = mock_cups
        mock_cups.getJobs.return_value = {123: {'job-state': 8}}  # aborted
        
        # Enable waiting
        self.config.set('printer.wait_for_completion', True)
        self.config.set('printer.job_timeout', 10)
        
        result = self.printer_manager._wait_for_job_completion(123)
        
        # Should detect failure and return False
        self.assertFalse(result)
    
    @patch('subprocess.run')
    def test_print_file_waits_for_completion_with_cups(self, mock_run):
        """Test that _print_file waits for job completion when using CUPS"""
        # Mock CUPS connection
        mock_cups = MagicMock()
        mock_cups.printFile.return_value = 456  # Job ID
        self.printer_manager.cups_connection = mock_cups
        
        # Mock job completion wait
        with patch.object(self.printer_manager, '_wait_for_job_completion', return_value=True) as mock_wait:
            with patch.object(self.printer_manager, 'get_default_printer', return_value='test_printer'):
                with patch.object(self.printer_manager, '_estimate_page_count', return_value=1):
                    
                    result = self.printer_manager._print_file('/tmp/test.txt', 'Test', 'text/plain')
                    
                    # Should succeed
                    self.assertTrue(result)
                    
                    # Should have waited for completion
                    mock_wait.assert_called_once_with(456)


if __name__ == '__main__':
    unittest.main()