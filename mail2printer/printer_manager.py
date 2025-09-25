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
from PIL import Image

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
                        return line
