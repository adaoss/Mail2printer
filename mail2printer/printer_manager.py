"""
Printer management functionality for Mail2printer service
"""

import os
import subprocess
import logging
import tempfile
import shutil
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import mimetypes
from PIL import Image

# Try to import pycups for CUPS integration
try:
    import cups
    HAS_CUPS = True
except ImportError:
    HAS_CUPS = False
    logging.warning("pycups not available, using system commands for printing")

logger = logging.getLogger(__name__)

# CUPS job state constants
JOB_STATE_PENDING = 3
JOB_STATE_HELD = 4
JOB_STATE_PROCESSING = 5
JOB_STATE_STOPPED = 6
JOB_STATE_CANCELED = 7
JOB_STATE_ABORTED = 8
JOB_STATE_COMPLETED = 9

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
        self._last_image_orientation = None  # Track orientation for image jobs
        self._active_jobs = {}  # Track active print jobs
        
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
            job_id, success = self._print_file(temp_path, title, 'text/plain')
            
            if success and job_id:
                # Wait for job to be spooled before cleanup
                self.wait_for_job_completion(job_id, timeout=10)
            else:
                # Even without job ID, wait briefly for file to be read
                time.sleep(2)
            
            # Clean up
            try:
                os.unlink(temp_path)
            except Exception as e:
                logger.warning(f"Failed to delete temp file {temp_path}: {e}")
            
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
                    job_id, success = self._print_file(pdf_path, title, 'application/pdf')
                    
                    if success and job_id:
                        # Wait for job to be spooled before cleanup
                        self.wait_for_job_completion(job_id, timeout=10)
                    else:
                        # Wait briefly for file to be read
                        time.sleep(2)
                    
                    try:
                        os.unlink(pdf_path)
                    except Exception as e:
                        logger.warning(f"Failed to delete temp file {pdf_path}: {e}")
                    
                    return success
            else:
                # Print HTML directly
                with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as temp_file:
                    temp_file.write(html)
                    temp_path = temp_file.name
                
                job_id, success = self._print_file(temp_path, title, 'text/html')
                
                if success and job_id:
                    self.wait_for_job_completion(job_id, timeout=10)
                else:
                    time.sleep(2)
                
                try:
                    os.unlink(temp_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temp file {temp_path}: {e}")
                
                return success
                
        except Exception as e:
            logger.error(f"Error printing HTML: {e}")
            return False
    
    def print_file_old(self, file_path: Path, title: str = None) -> bool:
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
        
        # Handle PDFs: Always print as-is in portrait orientation, no processing
        if content_type == "application/pdf":
            logger.info(f"Printing PDF as-is in portrait orientation: {file_path}")
            return self._print_pdf_as_is(str(file_path), title)
        
        # Handle Images: Convert to PDF in portrait orientation
        if content_type and content_type.startswith("image/"):
            # Only support PNG, JPG, JPEG formats
            supported_formats = ['image/png', 'image/jpeg', 'image/jpg']
            if content_type not in supported_formats:
                logger.error(f"Unsupported image format: {content_type}. Supported formats: PNG, JPG, JPEG")
                return False
                
            logger.info(f"Converting image to PDF in portrait orientation: {file_path}")
            pdf_path = self._image_to_pdf(file_path)
            if pdf_path:
                # Use image-specific print options (always portrait)
                result = self._print_file_with_image_options(pdf_path, title, "application/pdf")
                
                # Wait briefly for print spooling before cleanup
                if result:
                    time.sleep(2)
                
                try:
                    os.unlink(pdf_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temp file {pdf_path}: {e}")
                
                return result
            else:
                logger.error(f"Failed to convert image {file_path} to PDF.")
                return False

        job_id, success = self._print_file(str(file_path), title, content_type)
        return success

    def _print_pdf_as_is(self, file_path: str, title: str) -> bool:
        """
        Print a PDF file as-is in portrait orientation without any processing
        
        Args:
            file_path: Path to PDF file to print
            title: Job title
            
        Returns:
            True if print job submitted successfully
        """
        printer_name = self.get_default_printer()
        if not printer_name:
            logger.error("No printer available for printing")
            return False

        try:
            # Force portrait orientation for PDFs
            pdf_options = self.default_options.copy()
            pdf_options['orientation-requested'] = '3'  # Portrait orientation code
            
            # Use CUPS if available
            if self.cups_connection:
                job_id = self.cups_connection.printFile(
                    printer_name, file_path, title, pdf_options
                )
                logger.info(f"PDF print job {job_id} submitted to printer {printer_name}")
                return True
            else:
                # Fallback to lp command with portrait orientation
                cmd = [
                    'lp', '-d', printer_name,
                    '-t', title,
                    '-o', 'media=A4',
                    '-o', 'orientation-requested=3',  # Portrait
                    file_path
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    logger.info(f"PDF print job submitted via lp command to printer {printer_name}")
                    return True
                else:
                    logger.error(f"lp command failed: {result.stderr}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error printing PDF file {file_path}: {e}")
            return False

    def _image_to_pdf(self, image_path: Path) -> str or None:
        """
        Converts an image file to a PDF in portrait orientation for A4 paper.
        
        Features:
        - Always uses portrait orientation regardless of image dimensions
        - Scales image to fit A4 page with 10mm margins (or no margins if needed)
        - Centers image on the PDF page
        - Uses appropriate resolution for printing
        """
        try:
            with Image.open(image_path) as img:
                # Convert mode if necessary for PDF
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                
                # Get original image dimensions
                orig_width, orig_height = img.size
                logger.debug(f"Original image dimensions: {orig_width}x{orig_height}")
                
                # Always use portrait orientation as per requirements
                orientation = "portrait"
                
                # A4 dimensions in points (1 point = 1/72 inch)
                # A4 = 210mm x 297mm = 8.27" x 11.69" = 595 x 842 points
                A4_WIDTH_PT = 595
                A4_HEIGHT_PT = 842
                
                # Always use portrait page dimensions
                page_width = A4_WIDTH_PT   # 595
                page_height = A4_HEIGHT_PT # 842
                
                # Calculate margins in points (10mm = ~28.35 points)
                margin_pt = 28.35  # 10mm in points
                
                # Available space for image (with preferred margins)
                available_width = page_width - (2 * margin_pt)
                available_height = page_height - (2 * margin_pt)
                
                # Calculate scaling factor to fit image in available space
                scale_x = available_width / orig_width
                scale_y = available_height / orig_height
                scale_factor = min(scale_x, scale_y)
                
                # If image doesn't fit with margins, try without margins
                if scale_factor < 0.1:  # Image is way too big even with margins
                    logger.debug("Image too large for 10mm margins, using no margins")
                    available_width = page_width
                    available_height = page_height
                    scale_x = available_width / orig_width
                    scale_y = available_height / orig_height
                    scale_factor = min(scale_x, scale_y)
                    margin_pt = 0
                
                # Calculate final image dimensions
                final_width = int(orig_width * scale_factor)
                final_height = int(orig_height * scale_factor)
                
                logger.debug(f"Scaling factor: {scale_factor:.3f}")
                logger.debug(f"Final image dimensions: {final_width}x{final_height}")
                logger.debug(f"Using orientation: {orientation}")
                logger.debug(f"Using margins: {margin_pt:.1f}pt ({margin_pt/28.35:.1f}mm)")
                
                # Resize image if necessary
                if scale_factor != 1.0:
                    img = img.resize((final_width, final_height), Image.Resampling.LANCZOS)
                
                # Create new image with A4 page size and white background
                page_img = Image.new('RGB', (int(page_width), int(page_height)), 'white')
                
                # Calculate position to center the image
                x_pos = int((page_width - final_width) / 2)
                y_pos = int((page_height - final_height) / 2)
                
                # Paste the resized image onto the page
                page_img.paste(img, (x_pos, y_pos))
                
                # Save as PDF with appropriate DPI
                # 72 DPI is standard for PDF, higher DPI for better quality
                dpi = 150  # Good balance between quality and file size
                
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
                    # Note: PIL doesn't directly support setting page orientation in PDF
                    # The orientation is handled by the page dimensions we set above
                    page_img.save(tmp_pdf, "PDF", resolution=dpi)
                    logger.debug(f"Image converted to PDF: {tmp_pdf.name}")
                    
                    # Store orientation info for print job options (always portrait now)
                    self._last_image_orientation = orientation
                    
                    return tmp_pdf.name
                    
        except Exception as e:
            logger.error(f"Error converting image to PDF: {e}")
            return None
    
    def _print_file_with_image_options(self, file_path: str, title: str, content_type: str = None) -> bool:
        """
        Print a file with image-specific options (orientation, A4 paper size)
        
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
            
            # Create image-specific print options
            image_options = self.default_options.copy()
            
            # Force A4 paper size for images
            image_options['media'] = 'A4'
            
            # Use the orientation determined during image conversion
            if self._last_image_orientation:
                image_options['orientation-requested'] = self._get_orientation_code(
                    self._last_image_orientation
                )
                logger.debug(f"Using {self._last_image_orientation} orientation for image")
            
            # Use CUPS if available
            if self.cups_connection:
                job_id = self.cups_connection.printFile(
                    printer_name,
                    file_path,
                    title,
                    image_options
                )
                logger.info(f"Image print job submitted to CUPS: Job ID {job_id}, Printer: {printer_name}, Orientation: {self._last_image_orientation}")
                return True
            
            # Fallback: use lp command
            cmd = ['lp', '-d', printer_name, '-t', title]
            
            # Add options
            for key, value in image_options.items():
                cmd.extend(['-o', f'{key}={value}'])
            
            cmd.append(file_path)
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"Image print job submitted using lp: {result.stdout.strip()}, Orientation: {self._last_image_orientation}")
                return True
            else:
                logger.error(f"Print command failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error printing image file {file_path}: {e}")
            return False
            
    
    def _print_file(self, file_path: str, title: str, content_type: str = None) -> tuple:
        """
        Internal method to print a file
        
        Args:
            file_path: Path to file to print
            title: Job title
            content_type: MIME type of file
            
        Returns:
            Tuple of (job_id, success) where job_id is the print job ID (or None) and success is bool
        """
        printer_name = self.get_default_printer()
        if not printer_name:
            logger.error("No printer available for printing")
            return None, False
        
        try:
            # Check page limits
            max_pages = self.config.get('processing.max_pages_per_document', 50)
            if max_pages > 0:
                page_count = self._estimate_page_count(file_path, content_type)
                if page_count > max_pages:
                    logger.warning(f"Document exceeds page limit ({page_count} > {max_pages})")
                    return None, False
            
            # Use CUPS if available
            if self.cups_connection:
                job_id = self.cups_connection.printFile(
                    printer_name,
                    file_path,
                    title,
                    self.default_options
                )
                logger.info(f"Print job submitted to CUPS: Job ID {job_id}, Printer: {printer_name}")
                self._active_jobs[job_id] = {'title': title, 'file_path': file_path, 'time': time.time()}
                return job_id, True
            
            # Fallback: use lp command
            cmd = ['lp', '-d', printer_name, '-t', title]
            
            # Add options
            for key, value in self.default_options.items():
                cmd.extend(['-o', f'{key}={value}'])
            
            cmd.append(file_path)
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"Print job submitted using lp: {result.stdout.strip()}")
                # Try to extract job ID from lp output (format: "request id is PrinterName-jobid")
                try:
                    output = result.stdout.strip()
                    if 'request id is' in output:
                        job_id_str = output.split('request id is')[1].strip().split('-')[-1]
                        job_id = int(job_id_str)
                        self._active_jobs[job_id] = {'title': title, 'file_path': file_path, 'time': time.time()}
                        return job_id, True
                except Exception:
                    pass
                return None, True
            else:
                logger.error(f"Print command failed: {result.stderr}")
                return None, False
                
        except Exception as e:
            logger.error(f"Error printing file {file_path}: {e}")
            return None, False
    
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
            # Preprocess HTML to handle CID references that cause wkhtmltopdf errors
            processed_html = self._preprocess_html_for_pdf(html)
            
            # Try using wkhtmltopdf
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as html_file:
                html_file.write(processed_html)
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
                '--disable-external-links',  # Prevent CID protocol errors
                '--load-error-handling', 'ignore',  # Ignore resource loading errors
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
    
    def _preprocess_html_for_pdf(self, html: str) -> str:
        """
        Preprocess HTML content to handle issues that cause wkhtmltopdf errors
        
        Args:
            html: Original HTML content
            
        Returns:
            Processed HTML content safe for wkhtmltopdf
        """
        import re
        
        # Replace CID references with placeholder text to prevent protocol errors
        # Pattern matches: src="cid:..." or href="cid:..." 
        cid_pattern = r'(?i)(src|href)=["\']cid:[^"\']*["\']'
        
        def replace_cid(match):
            attr = match.group(1).lower()
            if attr == 'src':
                # For images, replace with a placeholder or remove the src entirely
                return 'src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==" alt="[Embedded Image]"'
            else:
                # For links, just remove the href to make it non-functional
                return 'href="#" title="[Embedded Content]"'
        
        processed_html = re.sub(cid_pattern, replace_cid, html)
        
        # Log if we made any replacements
        if processed_html != html:
            cid_count = len(re.findall(cid_pattern, html))
            logger.debug(f"Preprocessed HTML: replaced {cid_count} CID references")
        
        return processed_html
    
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
    
    def wait_for_job_completion(self, job_id: int, timeout: int = 30) -> bool:
        """
        Wait for print job to complete
        
        Args:
            job_id: Print job ID
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if job completed successfully
        """
        if not self.cups_connection:
            # Without CUPS, wait a fixed time for print spooling
            time.sleep(min(timeout, 5))
            return True
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                jobs = self.cups_connection.getJobs()
                if job_id not in jobs:
                    # Job completed (no longer in queue)
                    logger.debug(f"Print job {job_id} completed")
                    return True
                
                # Check job state
                job_state = jobs[job_id].get('job-state')
                if job_state in [JOB_STATE_CANCELED, JOB_STATE_ABORTED, JOB_STATE_COMPLETED]:
                    logger.debug(f"Print job {job_id} finished with state {job_state}")
                    return True
                
                # Job still processing, wait a bit
                time.sleep(0.5)
                
            except Exception as e:
                logger.warning(f"Error checking job {job_id} status: {e}")
                break
        
        logger.warning(f"Print job {job_id} did not complete within {timeout}s")
        return False
    
    def get_all_jobs(self) -> Dict[int, Dict[str, Any]]:
        """
        Get all print jobs
        
        Returns:
            Dictionary of job IDs to job information
        """
        if self.cups_connection:
            try:
                return self.cups_connection.getJobs()
            except Exception as e:
                logger.error(f"Error getting jobs: {e}")
        
        return {}
    
    def get_printer_stats(self) -> Dict[str, Any]:
        """
        Get printer statistics
        
        Returns:
            Dictionary with printer statistics
        """
        stats = {
            'printer_name': self.get_default_printer(),
            'available_printers': self.get_available_printers(),
            'active_jobs': len(self._active_jobs),
            'cups_available': HAS_CUPS and self.cups_connection is not None
        }
        
        if self.cups_connection:
            try:
                jobs = self.cups_connection.getJobs()
                stats['queued_jobs'] = len(jobs)
                stats['job_ids'] = list(jobs.keys())
            except Exception as e:
                logger.error(f"Error getting printer stats: {e}")
                stats['queued_jobs'] = 0
                stats['job_ids'] = []
        
        return stats
