"""
Printer management functionality for Mail2printer service
"""

import os
import subprocess
import logging
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
import mimetypes

# Try to import pycups for CUPS integration
try:
    import cups
    HAS_CUPS = True
except ImportError:
    HAS_CUPS = False
    logging.warning("pycups not available, using system commands for printing")

logger = logging.getLogger(__name__)

class PrintJob:
    """Represents a print job"""
    
    def __init__(self, content: str, content_type: str = 'text/plain', 
                 filename: str = 'email.txt', options: Dict[str, Any] = None):
        """
        Initialize print job
        
        Args:
            content: Content to print (text or file path)
            content_type: MIME type of content
            filename: Filename for the job
            options: Print options
        """
        self.content = content
        self.content_type = content_type
        self.filename = filename
        self.options = options or {}
        self.job_id = None
        self.status = 'pending'

class PrinterManager:
    """Manages printer operations for Mail2printer service"""
    
    def __init__(self, config):
        """
        Initialize printer manager
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.cups_connection = None
        self.available_printers = []
        
        if HAS_CUPS:
            try:
                self.cups_connection = cups.Connection()
                self.available_printers = list(self.cups_connection.getPrinters().keys())
                logger.info(f"CUPS connection established. Available printers: {self.available_printers}")
            except Exception as e:
                logger.warning(f"Failed to connect to CUPS: {e}")
                self.cups_connection = None
        
        self._setup_print_options()
    
    def _setup_print_options(self):
        """Setup default print options from configuration"""
        self.default_options = {
            'media': self.config.get('printer.paper_size', 'A4'),
            'orientation-requested': self._get_orientation_code(
                self.config.get('printer.orientation', 'portrait')
            ),
            'print-quality': self._get_quality_code(
                self.config.get('printer.quality', 'draft')
            ),
            'sides': 'two-sided-long-edge' if self.config.get('printer.duplex') else 'one-sided',
            'print-color-mode': 'color' if self.config.get('printer.color') else 'monochrome'
        }
    
    def _get_orientation_code(self, orientation: str) -> str:
        """Convert orientation string to CUPS code"""
        orientation_map = {
            'portrait': '3',
            'landscape': '4',
            'reverse-portrait': '5',
            'reverse-landscape': '6'
        }
        return orientation_map.get(orientation.lower(), '3')
    
    def _get_quality_code(self, quality: str) -> str:
        """Convert quality string to CUPS code"""
        quality_map = {
            'draft': '3',
            'normal': '4',
            'high': '5'
        }
        return quality_map.get(quality.lower(), '4')
    
    def get_available_printers(self) -> List[str]:
        """
        Get list of available printers
        
        Returns:
            List of printer names
        """
        if self.cups_connection:
            try:
                printers = self.cups_connection.getPrinters()
                return list(printers.keys())
            except Exception as e:
                logger.error(f"Error getting printers from CUPS: {e}")
        
        # Fallback: try to get printers using system commands
        try:
            result = subprocess.run(['lpstat', '-p'], capture_output=True, text=True)
            if result.returncode == 0:
                printers = []
                for line in result.stdout.split('\n'):
                    if line.startswith('printer '):
                        printer_name = line.split()[1]
                        printers.append(printer_name)
                return printers
        except Exception as e:
            logger.error(f"Error getting printers using lpstat: {e}")
        
        return []
    
    def get_default_printer(self) -> Optional[str]:
        """
        Get default printer name
        
        Returns:
            Default printer name or None
        """
        configured_printer = self.config.get('printer.name')
        if configured_printer and configured_printer != 'default':
            return configured_printer
        
        if self.cups_connection:
            try:
                return self.cups_connection.getDefault()
            except Exception as e:
                logger.warning(f"Error getting default printer from CUPS: {e}")
        
        # Fallback: try system command
        try:
            result = subprocess.run(['lpstat', '-d'], capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'system default destination:' in line:
                        return line.split(':')[1].strip()
        except Exception as e:
            logger.warning(f"Error getting default printer using lpstat: {e}")
        
        # Return first available printer as fallback
        available = self.get_available_printers()
        return available[0] if available else None
    
    def test_connection(self) -> bool:
        """
        Test printer connection
        
        Returns:
            True if printer is available
        """
        printer_name = self.get_default_printer()
        if not printer_name:
            logger.error("No printer available")
            return False
        
        if self.cups_connection:
            try:
                printers = self.cups_connection.getPrinters()
                printer_info = printers.get(printer_name)
                if printer_info:
                    logger.info(f"Printer '{printer_name}' is available: {printer_info.get('printer-info', '')}")
                    return True
            except Exception as e:
                logger.error(f"Error testing printer connection: {e}")
        
        # Fallback: test using system command
        try:
            result = subprocess.run(['lpstat', '-p', printer_name], capture_output=True, text=True)
            if result.returncode == 0 and 'enabled' in result.stdout.lower():
                logger.info(f"Printer '{printer_name}' is available")
                return True
        except Exception as e:
            logger.error(f"Error testing printer using lpstat: {e}")
        
        return False
    
    def print_text(self, text: str, title: str = 'Email Content') -> bool:
        """
        Print plain text content
        
        Args:
            text: Text to print
            title: Job title
            
        Returns:
            True if print job submitted successfully
        """
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as temp_file:
                temp_file.write(text)
                temp_path = temp_file.name
            
            # Print the file
            success = self._print_file(temp_path, title, 'text/plain')
            
            # Clean up
            os.unlink(temp_path)
            
            return success
            
        except Exception as e:
            logger.error(f"Error printing text: {e}")
            return False
    
    def print_html(self, html: str, title: str = 'Email Content') -> bool:
        """
        Print HTML content (convert to PDF first if configured)
        
        Args:
            html: HTML content to print
            title: Job title
            
        Returns:
            True if print job submitted successfully
        """
        try:
            if self.config.get('processing.convert_html_to_pdf', True):
                # Convert HTML to PDF first
                pdf_path = self._html_to_pdf(html, title)
                if pdf_path:
                    success = self._print_file(pdf_path, title, 'application/pdf')
                    os.unlink(pdf_path)
                    return success
            else:
                # Print HTML directly
                with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as temp_file:
                    temp_file.write(html)
                    temp_path = temp_file.name
                
                success = self._print_file(temp_path, title, 'text/html')
                os.unlink(temp_path)
                return success
                
        except Exception as e:
            logger.error(f"Error printing HTML: {e}")
            return False
    
    def print_file(self, file_path: Path, title: str = None) -> bool:
        """
        Print a file
        
        Args:
            file_path: Path to file to print
            title: Job title (defaults to filename)
            
        Returns:
            True if print job submitted successfully
        """
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return False
        
        title = title or file_path.name
        content_type, _ = mimetypes.guess_type(str(file_path))
        
        return self._print_file(str(file_path), title, content_type)
    
    def _print_file(self, file_path: str, title: str, content_type: str = None) -> bool:
        """
        Internal method to print a file
        
        Args:
            file_path: Path to file to print
            title: Job title
            content_type: MIME type of file
            
        Returns:
            True if print job submitted successfully
        """
        printer_name = self.get_default_printer()
        if not printer_name:
            logger.error("No printer available for printing")
            return False
        
        try:
            # Check page limits
            max_pages = self.config.get('processing.max_pages_per_document', 50)
            if max_pages > 0:
                page_count = self._estimate_page_count(file_path, content_type)
                if page_count > max_pages:
                    logger.warning(f"Document exceeds page limit ({page_count} > {max_pages})")
                    return False
            
            # Use CUPS if available
            if self.cups_connection:
                job_id = self.cups_connection.printFile(
                    printer_name,
                    file_path,
                    title,
                    self.default_options
                )
                logger.info(f"Print job submitted to CUPS: Job ID {job_id}, Printer: {printer_name}")
                return True
            
            # Fallback: use lp command
            cmd = ['lp', '-d', printer_name, '-t', title]
            
            # Add options
            for key, value in self.default_options.items():
                cmd.extend(['-o', f'{key}={value}'])
            
            cmd.append(file_path)
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"Print job submitted using lp: {result.stdout.strip()}")
                return True
            else:
                logger.error(f"Print command failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error printing file {file_path}: {e}")
            return False
    
    def _html_to_pdf(self, html: str, title: str) -> Optional[str]:
        """
        Convert HTML to PDF
        
        Args:
            html: HTML content
            title: Document title
            
        Returns:
            Path to generated PDF file or None
        """
        try:
            # Try using wkhtmltopdf
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as html_file:
                html_file.write(html)
                html_path = html_file.name
            
            pdf_path = html_path.replace('.html', '.pdf')
            
            cmd = [
                'wkhtmltopdf',
                '--page-size', self.config.get('printer.paper_size', 'A4'),
                '--orientation', self.config.get('printer.orientation', 'portrait'),
                '--margin-top', '20mm',
                '--margin-bottom', '20mm',
                '--margin-left', '20mm',
                '--margin-right', '20mm',
                html_path,
                pdf_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            os.unlink(html_path)
            
            if result.returncode == 0 and os.path.exists(pdf_path):
                logger.info(f"HTML converted to PDF: {pdf_path}")
                return pdf_path
            else:
                logger.warning(f"wkhtmltopdf failed: {result.stderr}")
                
        except FileNotFoundError:
            logger.warning("wkhtmltopdf not found, trying alternative methods")
        except Exception as e:
            logger.error(f"Error converting HTML to PDF: {e}")
        
        # Try using weasyprint as fallback
        try:
            import weasyprint
            
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as pdf_file:
                pdf_path = pdf_file.name
            
            weasyprint.HTML(string=html).write_pdf(pdf_path)
            logger.info(f"HTML converted to PDF using WeasyPrint: {pdf_path}")
            return pdf_path
            
        except ImportError:
            logger.warning("WeasyPrint not available")
        except Exception as e:
            logger.error(f"Error converting HTML to PDF with WeasyPrint: {e}")
        
        return None
    
    def _estimate_page_count(self, file_path: str, content_type: str) -> int:
        """
        Estimate number of pages in document
        
        Args:
            file_path: Path to file
            content_type: MIME type
            
        Returns:
            Estimated page count
        """
        try:
            if content_type == 'application/pdf':
                # Try to get PDF page count
                result = subprocess.run(['pdfinfo', file_path], capture_output=True, text=True)
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if line.startswith('Pages:'):
                            return int(line.split(':')[1].strip())
            
            elif content_type and content_type.startswith('text/'):
                # Estimate text pages (assuming ~60 lines per page, ~80 chars per line)
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    lines = len(content.split('\n'))
                    return max(1, lines // 60)
            
        except Exception as e:
            logger.warning(f"Error estimating page count: {e}")
        
        # Default conservative estimate
        return 1
    
    def get_print_status(self, job_id: int) -> str:
        """
        Get status of print job
        
        Args:
            job_id: Print job ID
            
        Returns:
            Job status string
        """
        if self.cups_connection:
            try:
                jobs = self.cups_connection.getJobs()
                if job_id in jobs:
                    return jobs[job_id]['job-state']
            except Exception as e:
                logger.error(f"Error getting job status: {e}")
        
        return 'unknown'
    
    def cancel_job(self, job_id: int) -> bool:
        """
        Cancel print job
        
        Args:
            job_id: Print job ID
            
        Returns:
            True if job cancelled successfully
        """
        if self.cups_connection:
            try:
                self.cups_connection.cancelJob(job_id)
                logger.info(f"Print job {job_id} cancelled")
                return True
            except Exception as e:
                logger.error(f"Error cancelling job {job_id}: {e}")
        
        return False