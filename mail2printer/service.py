"""
Main service module for Mail2printer
"""

import logging
import signal
import sys
import time
import threading
from pathlib import Path
from typing import List

from .config import Config
from .email_handler import EmailHandler, EmailMessage
from .printer_manager import PrinterManager

logger = logging.getLogger(__name__)

# Constants for attachment print job waiting
BASE_WAIT_TIME = 5  # Base wait time in seconds
WAIT_PER_ATTACHMENT = 2  # Additional seconds per attachment
MAX_WAIT_TIME = 30  # Maximum wait time in seconds

class Mail2PrinterService:
    """Main Mail2printer service"""
    
    def __init__(self, config: Config):
        """
        Initialize Mail2printer service
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.email_handler = EmailHandler(config)
        self.printer_manager = PrinterManager(config)
        self.running = False
        self.stats = {
            'emails_processed': 0,
            'emails_printed': 0,
            'print_jobs_failed': 0,
            'service_start_time': None
        }
        
        # Setup signal handlers
        self._setup_signal_handlers()
        
        # Validate configuration
        if not self.config.validate():
            raise ValueError("Invalid configuration")
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            self.stop()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def start(self):
        """Start the service"""
        logger.info("Starting Mail2printer service...")
        
        # Test connections
        if not self._test_connections():
            raise RuntimeError("Failed to establish required connections")
        
        self.running = True
        self.stats['service_start_time'] = time.time()
        
        logger.info("Mail2printer service started successfully")
    
    def stop(self):
        """Stop the service"""
        logger.info("Stopping Mail2printer service...")
        self.running = False
        
        # Disconnect from email server
        self.email_handler.disconnect()
        
        # Print final statistics
        self._log_statistics()
        
        logger.info("Mail2printer service stopped")
    
    def run(self, daemon: bool = False):
        """
        Run the service
        
        Args:
            daemon: Whether to run as daemon
        """
        if daemon:
            self._daemonize()
        
        self.start()
        
        try:
            # Start email checking loop
            self.email_handler.run_check_loop(self._process_emails)
        except Exception as e:
            logger.error(f"Service error: {e}")
            raise
        finally:
            self.stop()
    
    def _test_connections(self) -> bool:
        """
        Test all required connections
        
        Returns:
            True if all connections successful
        """
        logger.info("Testing connections...")
        
        # Test email connection
        if not self.email_handler.test_connection():
            logger.error("Email connection test failed")
            return False
        
        # Test printer connection
        if not self.printer_manager.test_connection():
            logger.error("Printer connection test failed")
            return False
        
        logger.info("All connection tests passed")
        return True
    
    def _process_emails(self, emails: List[EmailMessage]):
        """
        Process new emails
        
        Args:
            emails: List of email messages to process
        """
        for email_msg in emails:
            try:
                self._process_single_email(email_msg)
                self.stats['emails_processed'] += 1
                
            except Exception as e:
                logger.error(f"Error processing email from {email_msg.sender}: {e}")
    
    def _process_single_email(self, email_msg: EmailMessage):
        """
        Process a single email message
        
        Args:
            email_msg: Email message to process
        """
        logger.info(f"Processing email from {email_msg.sender}: {email_msg.subject}")
        
        printed_something = False
        
        # If email has attachments, only print attachments (not email body)
        if self.config.get('processing.print_attachments', True) and email_msg.attachments:
            if self._print_attachments(email_msg):
                printed_something = True
                logger.info(f"Printed attachments only for email with attachments from {email_msg.sender}")
        # If no attachments, print email content
        elif self._should_print_content(email_msg):
            if self._print_email_content(email_msg):
                printed_something = True
                logger.info(f"Printed email content (no attachments) from {email_msg.sender}")
        
        if printed_something:
            self.stats['emails_printed'] += 1
            logger.info(f"Successfully printed email from {email_msg.sender}")
        else:
            logger.warning(f"No content printed for email from {email_msg.sender}")
    
    def _should_print_content(self, email_msg: EmailMessage) -> bool:
        """
        Check if email content should be printed
        
        Args:
            email_msg: Email message
            
        Returns:
            True if content should be printed
        """
        has_text = bool(email_msg.text_content.strip())
        has_html = bool(email_msg.html_content.strip())
        
        print_text = self.config.get('processing.print_text_emails', True)
        print_html = self.config.get('processing.print_html_emails', True)
        
        return (has_text and print_text) or (has_html and print_html)
    
    def _print_email_content(self, email_msg: EmailMessage) -> bool:
        """
        Print email content
        
        Args:
            email_msg: Email message
            
        Returns:
            True if content was printed successfully
        """
        title = f"Email: {email_msg.subject}"
        
        # Prepare email header
        header = f"""From: {email_msg.sender}
To: {email_msg.recipient}
Subject: {email_msg.subject}
Date: {email_msg.date}

{'=' * 50}

"""
        
        # Print HTML content if available and preferred
        if email_msg.html_content and self.config.get('processing.print_html_emails', True):
            try:
                # Add header to HTML
                html_content = f"""
                <html>
                <head><title>{email_msg.subject}</title></head>
                <body>
                <pre>{header}</pre>
                {email_msg.html_content}
                </body>
                </html>
                """
                
                if self.printer_manager.print_html(html_content, title):
                    return True
                    
            except Exception as e:
                logger.warning(f"Failed to print HTML content: {e}")
        
        # Fallback to text content
        if email_msg.text_content and self.config.get('processing.print_text_emails', True):
            try:
                text_content = header + email_msg.text_content
                return self.printer_manager.print_text(text_content, title)
                
            except Exception as e:
                logger.error(f"Failed to print text content: {e}")
        
        return False
    
    def _print_attachments(self, email_msg: EmailMessage) -> bool:
        """
        Print email attachments
        
        Args:
            email_msg: Email message
            
        Returns:
            True if at least one attachment was printed
        """
        if not email_msg.attachments:
            return False
        
        printed_count = 0
        
        # Save attachments to temporary directory
        import tempfile
        temp_dir = tempfile.TemporaryDirectory()
        try:
            temp_path = Path(temp_dir.name)
            saved_files = email_msg.save_attachments(temp_path)
            
            for file_path in saved_files:
                try:
                    title = f"Attachment: {file_path.name}"
                    if self.printer_manager.print_file(file_path, title):
                        printed_count += 1
                        logger.info(f"Printed attachment: {file_path.name}")
                    else:
                        logger.warning(f"Failed to print attachment: {file_path.name}")
                        self.stats['print_jobs_failed'] += 1
                        
                except Exception as e:
                    logger.error(f"Error printing attachment {file_path.name}: {e}")
                    self.stats['print_jobs_failed'] += 1
            
            # Wait for print jobs to complete before cleanup
            # Give extra time for multiple attachments
            wait_time = min(BASE_WAIT_TIME + (printed_count * WAIT_PER_ATTACHMENT), MAX_WAIT_TIME)
            logger.debug(f"Waiting {wait_time}s for {printed_count} attachment(s) to spool")
            time.sleep(wait_time)
            
        finally:
            # Clean up temporary directory
            temp_dir.cleanup()
        
        return printed_count > 0
    
    def _log_statistics(self):
        """Log service statistics"""
        if self.stats['service_start_time']:
            uptime = time.time() - self.stats['service_start_time']
            uptime_str = f"{uptime:.1f} seconds"
            if uptime > 3600:
                hours = int(uptime // 3600)
                minutes = int((uptime % 3600) // 60)
                uptime_str = f"{hours}h {minutes}m"
            elif uptime > 60:
                minutes = int(uptime // 60)
                seconds = int(uptime % 60)
                uptime_str = f"{minutes}m {seconds}s"
        else:
            uptime_str = "unknown"
        
        logger.info("=== Mail2printer Service Statistics ===")
        logger.info(f"Service uptime: {uptime_str}")
        logger.info(f"Emails processed: {self.stats['emails_processed']}")
        logger.info(f"Emails printed: {self.stats['emails_printed']}")
        logger.info(f"Print jobs failed: {self.stats['print_jobs_failed']}")
        
        if self.stats['emails_processed'] > 0:
            success_rate = (self.stats['emails_printed'] / self.stats['emails_processed']) * 100
            logger.info(f"Success rate: {success_rate:.1f}%")
    
    def _daemonize(self):
        """Daemonize the process (Unix only)"""
        try:
            import os
            
            # First fork
            pid = os.fork()
            if pid > 0:
                sys.exit(0)  # Exit parent
            
            # Decouple from parent environment
            os.chdir('/')
            os.setsid()
            os.umask(0)
            
            # Second fork
            pid = os.fork()
            if pid > 0:
                sys.exit(0)  # Exit second parent
            
            # Redirect standard file descriptors
            sys.stdout.flush()
            sys.stderr.flush()
            
            with open('/dev/null', 'r') as si:
                os.dup2(si.fileno(), sys.stdin.fileno())
            with open('/dev/null', 'w') as so:
                os.dup2(so.fileno(), sys.stdout.fileno())
            with open('/dev/null', 'w') as se:
                os.dup2(se.fileno(), sys.stderr.fileno())
            
            logger.info("Service daemonized successfully")
            
        except AttributeError:
            logger.warning("Daemonization not supported on this platform")
        except Exception as e:
            logger.error(f"Failed to daemonize: {e}")
            raise
    
    def get_status(self) -> dict:
        """
        Get service status
        
        Returns:
            Status dictionary
        """
        return {
            'running': self.running,
            'stats': self.stats,
            'config': {
                'email_server': self.config.get('email.server'),
                'printer': self.printer_manager.get_default_printer(),
                'check_interval': self.config.get('email.check_interval')
            }
        }