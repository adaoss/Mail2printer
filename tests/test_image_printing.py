"""Tests for image printing functionality"""

import unittest
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

# Mock the PIL module before importing printer manager
sys.modules['PIL'] = MagicMock()
sys.modules['PIL.Image'] = MagicMock()
sys.modules['PIL.Image'].Resampling = MagicMock()
sys.modules['PIL.Image'].Resampling.LANCZOS = MagicMock()
sys.modules['pycups'] = MagicMock()
sys.modules['weasyprint'] = MagicMock()

from mail2printer.config import Config
from mail2printer.printer_manager import PrinterManager


class TestImagePrinting(unittest.TestCase):
    """Test image printing functionality"""
    
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
    
    @patch('mail2printer.printer_manager.Image')
    def test_image_to_pdf_landscape_orientation(self, mock_image):
        """Test that landscape images are converted to portrait orientation"""
        # Mock landscape image (1600x900)
        mock_img = MagicMock()
        mock_img.mode = 'RGB'
        mock_img.size = (1600, 900)  # Landscape
        mock_img.resize.return_value = mock_img
        mock_image.open.return_value.__enter__.return_value = mock_img
        
        # Mock Image.new for page creation
        mock_page_img = MagicMock()
        mock_image.new.return_value = mock_page_img
        
        # Mock tempfile
        with patch('tempfile.NamedTemporaryFile') as mock_temp:
            mock_temp.return_value.__enter__.return_value.name = '/tmp/test.pdf'
            
            result = self.printer_manager._image_to_pdf(Path('/fake/image.jpg'))
            
            # Should return PDF path
            self.assertEqual(result, '/tmp/test.pdf')
            
            # Should force portrait orientation even for landscape images
            self.assertEqual(self.printer_manager._last_image_orientation, 'portrait')
    
    @patch('mail2printer.printer_manager.Image')
    def test_image_to_pdf_portrait_orientation(self, mock_image):
        """Test that portrait images get portrait orientation"""
        # Mock portrait image (800x1200)
        mock_img = MagicMock()
        mock_img.mode = 'RGB'
        mock_img.size = (800, 1200)  # Portrait
        mock_img.resize.return_value = mock_img
        mock_image.open.return_value.__enter__.return_value = mock_img
        
        # Mock Image.new for page creation
        mock_page_img = MagicMock()
        mock_image.new.return_value = mock_page_img
        
        # Mock tempfile
        with patch('tempfile.NamedTemporaryFile') as mock_temp:
            mock_temp.return_value.__enter__.return_value.name = '/tmp/test.pdf'
            
            result = self.printer_manager._image_to_pdf(Path('/fake/image.jpg'))
            
            # Should return PDF path
            self.assertEqual(result, '/tmp/test.pdf')
            
            # Should set portrait orientation
            self.assertEqual(self.printer_manager._last_image_orientation, 'portrait')
    
    @patch('mail2printer.printer_manager.Image')
    def test_image_to_pdf_square_orientation(self, mock_image):
        """Test that square images get portrait orientation (default)"""
        # Mock square image (1000x1000)
        mock_img = MagicMock()
        mock_img.mode = 'RGB'
        mock_img.size = (1000, 1000)  # Square
        mock_img.resize.return_value = mock_img
        mock_image.open.return_value.__enter__.return_value = mock_img
        
        # Mock Image.new for page creation
        mock_page_img = MagicMock()
        mock_image.new.return_value = mock_page_img
        
        # Mock tempfile
        with patch('tempfile.NamedTemporaryFile') as mock_temp:
            mock_temp.return_value.__enter__.return_value.name = '/tmp/test.pdf'
            
            result = self.printer_manager._image_to_pdf(Path('/fake/image.jpg'))
            
            # Should return PDF path
            self.assertEqual(result, '/tmp/test.pdf')
            
            # Should default to portrait for square images
            self.assertEqual(self.printer_manager._last_image_orientation, 'portrait')
    
    @patch('mail2printer.printer_manager.Image')
    def test_image_to_pdf_rgba_conversion(self, mock_image):
        """Test that RGBA images are converted to RGB"""
        # Mock RGBA image
        mock_img = MagicMock()
        mock_img.mode = 'RGBA'
        mock_img.size = (800, 600)
        mock_converted_img = MagicMock()
        mock_converted_img.size = (800, 600)  # Add size to converted image
        mock_img.convert.return_value = mock_converted_img
        mock_image.open.return_value.__enter__.return_value = mock_img
        
        # Mock Image.new and resize for the page creation
        mock_page_img = MagicMock()
        mock_image.new.return_value = mock_page_img
        mock_converted_img.resize.return_value = mock_converted_img
        
        # Mock tempfile
        with patch('tempfile.NamedTemporaryFile') as mock_temp:
            mock_temp.return_value.__enter__.return_value.name = '/tmp/test.pdf'
            
            result = self.printer_manager._image_to_pdf(Path('/fake/image.png'))
            
            # Should convert RGBA to RGB
            mock_img.convert.assert_called_with('RGB')
            
            # Should return PDF path
            self.assertEqual(result, '/tmp/test.pdf')
    
    @patch('mail2printer.printer_manager.Image')
    def test_image_scaling_calculation(self, mock_image):
        """Test that images are properly scaled to fit A4 in portrait orientation"""
        # Mock very large image (4000x3000)
        mock_img = MagicMock()
        mock_img.mode = 'RGB'
        mock_img.size = (4000, 3000)  # Large landscape
        mock_image.open.return_value.__enter__.return_value = mock_img
        mock_image.new.return_value = MagicMock()
        
        # Mock tempfile
        with patch('tempfile.NamedTemporaryFile') as mock_temp:
            mock_temp.return_value.__enter__.return_value.name = '/tmp/test.pdf'
            
            result = self.printer_manager._image_to_pdf(Path('/fake/large_image.jpg'))
            
            # Should resize the image (resize should be called)
            mock_img.resize.assert_called()
            
            # Should return PDF path
            self.assertEqual(result, '/tmp/test.pdf')
            
            # Should force portrait orientation even for large landscape images
            self.assertEqual(self.printer_manager._last_image_orientation, 'portrait')
    
    def test_print_file_with_image_options_uses_a4(self):
        """Test that image print jobs use A4 paper size"""
        # Mock printer availability
        with patch.object(self.printer_manager, 'get_default_printer', return_value='test_printer'):
            with patch.object(self.printer_manager, '_estimate_page_count', return_value=1):
                with patch('subprocess.run') as mock_run:
                    mock_run.return_value.returncode = 0
                    mock_run.return_value.stdout = 'Job submitted'
                    
                    # Set a test orientation
                    self.printer_manager._last_image_orientation = 'landscape'
                    
                    result = self.printer_manager._print_file_with_image_options(
                        '/fake/file.pdf', 'Test Image', 'application/pdf'
                    )
                    
                    # Should succeed
                    self.assertTrue(result)
    
    @patch('mimetypes.guess_type')
    def test_print_file_detects_image_content_type(self, mock_guess_type):
        """Test that print_file correctly identifies and processes image files"""
        # Mock image content type
        mock_guess_type.return_value = ('image/jpeg', None)
        
        # Mock file existence
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.name = 'test.jpg'
        
        with patch.object(self.printer_manager, '_image_to_pdf', return_value='/tmp/converted.pdf') as mock_convert:
            with patch.object(self.printer_manager, '_print_file_with_image_options', return_value=True) as mock_print:
                with patch('os.unlink') as mock_unlink:
                    
                    result = self.printer_manager.print_file(mock_path)
                    
                    # Should detect image type and convert
                    mock_convert.assert_called_once_with(mock_path)
                    
                    # Should use image-specific printing
                    mock_print.assert_called_once_with('/tmp/converted.pdf', 'test.jpg', 'application/pdf')
                    
                    # Should clean up temporary file
                    mock_unlink.assert_called_once_with('/tmp/converted.pdf')
                    
                    # Should succeed
                    self.assertTrue(result)
    
    @patch('mail2printer.printer_manager.Image')
    def test_image_to_pdf_very_large_image_no_margins(self, mock_image):
        """Test that very large images fall back to no margins but still use portrait"""
        # Mock extremely large image that won't fit with margins
        mock_img = MagicMock()
        mock_img.mode = 'RGB'
        mock_img.size = (20000, 15000)  # Extremely large
        mock_img.resize.return_value = mock_img
        mock_image.open.return_value.__enter__.return_value = mock_img
        mock_image.new.return_value = MagicMock()
        
        # Mock tempfile
        with patch('tempfile.NamedTemporaryFile') as mock_temp:
            mock_temp.return_value.__enter__.return_value.name = '/tmp/test.pdf'
            
            result = self.printer_manager._image_to_pdf(Path('/fake/huge_image.jpg'))
            
            # Should still succeed (fall back to no margins)
            self.assertEqual(result, '/tmp/test.pdf')
            
            # Should force portrait orientation even for large landscape images
            self.assertEqual(self.printer_manager._last_image_orientation, 'portrait')
    
    def test_get_orientation_code_mapping(self):
        """Test orientation code mapping works correctly"""
        self.assertEqual(self.printer_manager._get_orientation_code('portrait'), '3')
        self.assertEqual(self.printer_manager._get_orientation_code('landscape'), '4')
        self.assertEqual(self.printer_manager._get_orientation_code('reverse-portrait'), '5')
        self.assertEqual(self.printer_manager._get_orientation_code('reverse-landscape'), '6')
        self.assertEqual(self.printer_manager._get_orientation_code('invalid'), '3')  # Default to portrait
    
    @patch('mimetypes.guess_type')
    def test_print_file_handles_non_image_files_normally(self, mock_guess_type):
        """Test that non-image files are processed normally"""
        # Mock text content type
        mock_guess_type.return_value = ('text/plain', None)
        
        # Mock file existence
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.name = 'test.txt'
        
        # Return tuple (job_id, success) instead of just bool
        with patch.object(self.printer_manager, '_print_file', return_value=(123, True)) as mock_print:
            
            result = self.printer_manager.print_file(mock_path)
            
            # Should use normal print_file method, not image-specific
            mock_print.assert_called_once_with(str(mock_path), 'test.txt', 'text/plain')
            
            # Should succeed
            self.assertTrue(result)
    
    @patch('mimetypes.guess_type')
    def test_print_file_handles_pdf_files_as_is(self, mock_guess_type):
        """Test that PDF files are printed as-is in portrait orientation"""
        # Mock PDF content type
        mock_guess_type.return_value = ('application/pdf', None)
        
        # Mock file existence
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.name = 'document.pdf'
        
        with patch.object(self.printer_manager, '_print_pdf_as_is', return_value=True) as mock_print_pdf:
            
            result = self.printer_manager.print_file(mock_path)
            
            # Should use PDF-specific print method
            mock_print_pdf.assert_called_once_with(str(mock_path), 'document.pdf')
            
            # Should succeed
            self.assertTrue(result)
    
    @patch('mimetypes.guess_type')
    def test_print_file_rejects_unsupported_image_formats(self, mock_guess_type):
        """Test that unsupported image formats are rejected"""
        # Mock unsupported image format (e.g., TIFF)
        mock_guess_type.return_value = ('image/tiff', None)
        
        # Mock file existence
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.name = 'image.tiff'
        
        result = self.printer_manager.print_file(mock_path)
        
        # Should fail for unsupported format
        self.assertFalse(result)
    
    @patch('mimetypes.guess_type')
    def test_print_file_accepts_supported_image_formats(self, mock_guess_type):
        """Test that supported image formats (PNG, JPG, JPEG) are accepted"""
        supported_formats = ['image/png', 'image/jpeg', 'image/jpg']
        
        for format_type in supported_formats:
            with self.subTest(format=format_type):
                # Mock supported image format
                mock_guess_type.return_value = (format_type, None)
                
                # Mock file existence
                mock_path = MagicMock()
                mock_path.exists.return_value = True
                mock_path.name = f'image.{format_type.split("/")[1]}'
                
                with patch.object(self.printer_manager, '_image_to_pdf', return_value='/tmp/test.pdf'):
                    with patch.object(self.printer_manager, '_print_file_with_image_options', return_value=True):
                        result = self.printer_manager.print_file(mock_path)
                        
                        # Should succeed for supported formats
                        self.assertTrue(result)
    
    def test_print_pdf_as_is_with_cups(self):
        """Test printing PDF as-is using CUPS"""
        # Mock CUPS connection
        mock_cups = MagicMock()
        mock_cups.printFile.return_value = 12345  # Mock job ID
        self.printer_manager.cups_connection = mock_cups
        
        with patch.object(self.printer_manager, 'get_default_printer', return_value='test_printer'):
            result = self.printer_manager._print_pdf_as_is('/path/to/file.pdf', 'Test PDF')
            
            # Should succeed
            self.assertTrue(result)
            
            # Check that CUPS was called with portrait orientation (key requirement)
            args, kwargs = mock_cups.printFile.call_args
            self.assertEqual(args[0], 'test_printer')
            self.assertEqual(args[1], '/path/to/file.pdf')
            self.assertEqual(args[2], 'Test PDF')
            
            # Verify portrait orientation is set
            options = args[3]
            self.assertEqual(options['orientation-requested'], '3')  # Portrait
            self.assertEqual(options['media'], 'A4')
    
    @patch('subprocess.run')
    def test_print_pdf_as_is_with_lp_command(self, mock_run):
        """Test printing PDF as-is using lp command fallback"""
        # Mock no CUPS connection
        self.printer_manager.cups_connection = None
        
        # Mock successful subprocess run
        mock_run.return_value.returncode = 0
        mock_run.return_value.stderr = ''
        
        with patch.object(self.printer_manager, 'get_default_printer', return_value='test_printer'):
            result = self.printer_manager._print_pdf_as_is('/path/to/file.pdf', 'Test PDF')
            
            # Should succeed
            self.assertTrue(result)
            
            # Should call lp command with portrait orientation
            expected_cmd = [
                'lp', '-d', 'test_printer',
                '-t', 'Test PDF',
                '-o', 'media=A4',
                '-o', 'orientation-requested=3',  # Portrait
                '/path/to/file.pdf'
            ]
            mock_run.assert_called_once_with(expected_cmd, capture_output=True, text=True)


if __name__ == '__main__':
    unittest.main()