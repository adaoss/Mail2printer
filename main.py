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
import threading
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

def start_api_server(service, config):
    """Start the REST API server in a separate thread"""
    from mail2printer import api
    
    # Set the service instance for API access
    api.set_service(service)
    
    # Set API key if configured
    api_key = config.get('api.key')
    if api_key:
        api.set_api_key(api_key)
        logging.info("API key authentication enabled")
    else:
        logging.warning("API key not configured - API will be open to all requests")
    
    # Get API configuration
    api_host = config.get('api.host', '0.0.0.0')
    api_port = config.get('api.port', 5000)
    api_debug = config.get('api.debug', False)
    
    # Start API server in separate thread
    api_thread = threading.Thread(
        target=api.run_api_server,
        args=(api_host, api_port, api_debug),
        daemon=True
    )
    api_thread.start()
    logging.info(f"API server started on {api_host}:{api_port}")

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
    parser.add_argument('--api-only', action='store_true',
                       help='Run only the API server (no email processing)')
    parser.add_argument('--no-api', action='store_true',
                       help='Disable the API server')
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
        
        # Start API server if enabled
        if not args.no_api and config.get('api.enabled', True):
            start_api_server(service, config)
        
        # Run main service unless API-only mode
        if not args.api_only:
            service.run(daemon=args.daemon)
        else:
            # API-only mode: just keep the main thread alive
            logger.info("Running in API-only mode")
            import time
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Shutting down...")
                
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Service error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()