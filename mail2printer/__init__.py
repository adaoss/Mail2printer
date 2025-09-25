"""
Mail2printer - Email to Printer Service

A Python service that automatically prints incoming emails.
"""

__version__ = "1.0.0"
__author__ = "Mail2printer Team"
__email__ = "support@mail2printer.com"

from .config import Config
from .email_handler import EmailHandler
from .printer_manager import PrinterManager
from .service import Mail2PrinterService

__all__ = [
    'Config',
    'EmailHandler', 
    'PrinterManager',
    'Mail2PrinterService'
]