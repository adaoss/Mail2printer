#!/usr/bin/env python3
"""
Mail2printer - Email to Printer Service

A service that receives emails and prints them automatically.
Supports various email formats, attachments, and printer configurations.
"""

import sys
import os
import logging
import argparse
from pathlib import Path

# Add current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import our modules
from mail2printer.config import Config
from mail2printer.email_handler import EmailHandler
from mail2printer.printer_manager import PrinterManager
from mail2printer.service import Mail2PrinterService

def setup_logging(config):
    """Setup logging configuration"""
    log_level = getattr(logging, config.get('logging', {}).get('level', 'INFO').upper())
    log_format = config.get('logging', {}).get('format', 
                          '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(config.get('logging', {}).get('file', 'mail2printer.log'))
        ]
    )

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Mail2printer - Email to Printer Service')
    parser.add_argument('--config', '-c', default='config.yaml',
                       help='Configuration file path (default: config.yaml)')
    parser.add_argument('--daemon', '-d', action='store_true',
                       help='Run as daemon')
    parser.add_argument('--test-printer', action='store_true',
                       help='Test printer connection and exit')
    parser.add_argument('--test-email', action='store_true',
                       help='Test email connection and exit')
    parser.add_argument('--version', action='version', version='Mail2printer 1.0.0')
    
    args = parser.parse_args()
    
    # Load configuration
    try:
        config = Config(args.config)
        if not os.path.exists(args.config):
            print(f"Warning: Configuration file '{args.config}' not found, using defaults")
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)
    
    # Setup logging
    setup_logging(config.data)
    logger = logging.getLogger(__name__)
    
    logger.info("Starting Mail2printer service...")
    
    # Test modes
    if args.test_printer:
        printer_manager = PrinterManager(config)
        if printer_manager.test_connection():
            print("Printer connection: OK")
            sys.exit(0)
        else:
            print("Printer connection: FAILED")
            sys.exit(1)
    
    if args.test_email:
        email_handler = EmailHandler(config)
        if email_handler.test_connection():
            print("Email connection: OK")
            sys.exit(0)
        else:
            print("Email connection: FAILED")
            sys.exit(1)
    
    # Start the service
    try:
        service = Mail2PrinterService(config)
        service.run(daemon=args.daemon)
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Service error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()