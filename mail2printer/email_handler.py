"""
Email handling functionality for Mail2printer service
"""

import imaplib
import email
import logging
import time
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import tempfile
import mimetypes

logger = logging.getLogger(__name__)

class EmailMessage:
    """Represents an email message with all its components"""
    
    def __init__(self, raw_message: email.message.EmailMessage, max_attachment_size: int = 10485760):
        """
        Initialize email message
        
        Args:
            raw_message: Raw email message from imaplib
            max_attachment_size: Maximum attachment size in bytes
        """
        self.raw_message = raw_message
        self.max_attachment_size = max_attachment_size
        self.subject = self._decode_header(raw_message.get('Subject', ''))
        self.sender = self._decode_header(raw_message.get('From', ''))
        self.recipient = self._decode_header(raw_message.get('To', ''))
        self.date = raw_message.get('Date', '')
        self.message_id = raw_message.get('Message-ID', '')
        
        # Extract message content
        self.text_content = ""
        self.html_content = ""
        self.attachments = []
        
        self._parse_content()
        
    def _decode_header(self, header: str) -> str:
        """Decode email header"""
        if not header:
            return ""
        
        decoded_parts = email.header.decode_header(header)
        decoded_header = ""
        
        for part, charset in decoded_parts:
            if isinstance(part, bytes):
                try:
                    decoded_header += part.decode(charset or 'utf-8')
                except (UnicodeDecodeError, LookupError):
                    decoded_header += part.decode('utf-8', errors='ignore')
            else:
                decoded_header += part
                
        return decoded_header
    
    def _parse_content(self):
        """Parse email content and attachments"""
        if self.raw_message.is_multipart():
            for part in self.raw_message.walk():
                self._process_part(part)
        else:
            self._process_part(self.raw_message)
    
    def _process_part(self, part):
        """Process a single email part"""
        content_type = part.get_content_type()
        content_disposition = str(part.get('Content-Disposition', ''))
        
        # Handle attachments
        if 'attachment' in content_disposition:
            self._handle_attachment(part)
        # Handle inline content
        elif content_type == 'text/plain' and 'attachment' not in content_disposition:
            try:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or 'utf-8'
                    self.text_content += payload.decode(charset, errors='ignore')
            except Exception as e:
                logger.warning(f"Error decoding text content: {e}")
                
        elif content_type == 'text/html' and 'attachment' not in content_disposition:
            try:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or 'utf-8'
                    self.html_content += payload.decode(charset, errors='ignore')
            except Exception as e:
                logger.warning(f"Error decoding HTML content: {e}")
    
    def _handle_attachment(self, part):
        """Handle email attachment"""
        filename = part.get_filename()
        if not filename:
            return
            
        filename = self._decode_header(filename)
        content_type = part.get_content_type()
        
        try:
            payload = part.get_payload(decode=True)
            if payload:
                # Check attachment size before storing in memory
                attachment_size = len(payload)
                
                if attachment_size > self.max_attachment_size:
                    logger.warning(f"Attachment {filename} too large ({attachment_size} bytes), skipping")
                    return
                    
                attachment = {
                    'filename': filename,
                    'content_type': content_type,
                    'size': attachment_size,
                    'data': payload
                }
                self.attachments.append(attachment)
                logger.debug(f"Found attachment: {filename} ({content_type}, {attachment_size} bytes)")
        except Exception as e:
            logger.warning(f"Error processing attachment {filename}: {e}")
    
    def save_attachments(self, directory: Path) -> List[Path]:
        """
        Save attachments to directory
        
        Args:
            directory: Directory to save attachments
            
        Returns:
            List of saved file paths
        """
        saved_files = []
        directory.mkdir(parents=True, exist_ok=True)
        
        for attachment in self.attachments:
            try:
                filename = attachment['filename']
                # Sanitize filename
                filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
                
                file_path = directory / filename
                with open(file_path, 'wb') as f:
                    f.write(attachment['data'])
                
                saved_files.append(file_path)
                logger.info(f"Saved attachment: {file_path}")
                
            except Exception as e:
                logger.error(f"Error saving attachment {attachment['filename']}: {e}")
        
        return saved_files

class EmailHandler:
    """Handles email operations for Mail2printer service"""
    
    def __init__(self, config):
        """
        Initialize email handler
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.imap_connection = None
        self.last_check_time = 0
        self._processed_message_ids = set()  # Track processed emails to prevent duplicates
        
    def connect(self) -> bool:
        """
        Connect to email server
        
        Returns:
            True if connection successful
        """
        try:
            server = self.config.get('email.server')
            port = self.config.get('email.port')
            use_ssl = self.config.get('email.use_ssl')
            
            if use_ssl:
                self.imap_connection = imaplib.IMAP4_SSL(server, port)
            else:
                self.imap_connection = imaplib.IMAP4(server, port)
            
            username = self.config.get('email.username')
            password = self.config.get('email.password')
            
            self.imap_connection.login(username, password)
            logger.info(f"Connected to email server: {server}:{port}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to email server: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from email server"""
        if self.imap_connection:
            try:
                self.imap_connection.close()
                self.imap_connection.logout()
                logger.info("Disconnected from email server")
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
            finally:
                self.imap_connection = None
    
    def test_connection(self) -> bool:
        """
        Test email server connection
        
        Returns:
            True if connection test successful
        """
        if self.connect():
            self.disconnect()
            return True
        return False
    
    def check_new_emails(self) -> List[EmailMessage]:
        """
        Check for new emails
        
        Returns:
            List of new email messages
        """
        if not self.imap_connection:
            if not self.connect():
                return []
        
        emails = []
        try:
            inbox_folder = self.config.get('email.inbox_folder', 'INBOX')
            self.imap_connection.select(inbox_folder)
            
            # Search for unread emails
            search_criteria = '(UNSEEN)'
            
            # Apply sender filters if configured
            allowed_senders = self.config.get('filters.allowed_senders', [])
            if allowed_senders:
                sender_criteria = ' OR '.join([f'FROM "{sender}"' for sender in allowed_senders])
                search_criteria = f'({search_criteria} ({sender_criteria}))'
            
            blocked_senders = self.config.get('filters.blocked_senders', [])
            if blocked_senders:
                for sender in blocked_senders:
                    search_criteria = f'({search_criteria} NOT FROM "{sender}")'
            
            status, message_ids = self.imap_connection.search(None, search_criteria)
            
            if status != 'OK':
                logger.warning(f"Email search failed: {status}")
                return emails
            
            for msg_id in message_ids[0].split():
                try:
                    # Fetch email
                    status, msg_data = self.imap_connection.fetch(msg_id, '(RFC822)')
                    if status != 'OK':
                        continue
                    
                    # Parse email
                    raw_email = email.message_from_bytes(msg_data[0][1])
                    max_attachment_size = self.config.get('filters.max_attachment_size', 10485760)
                    email_message = EmailMessage(raw_email, max_attachment_size)
                    
                    # Check if already processed (prevent duplicates)
                    if email_message.message_id in self._processed_message_ids:
                        logger.debug(f"Skipping already processed email: {email_message.message_id}")
                        continue
                    
                    # Apply filters
                    if self._should_process_email(email_message):
                        # Mark as read IMMEDIATELY to prevent reprocessing if service crashes
                        if self.config.get('email.mark_as_read'):
                            try:
                                self.imap_connection.store(msg_id, '+FLAGS', '\\Seen')
                            except Exception as e:
                                logger.warning(f"Failed to mark email as read: {e}")
                        
                        # Mark for deletion if configured (but don't expunge yet)
                        if self.config.get('email.delete_after_print'):
                            try:
                                self.imap_connection.store(msg_id, '+FLAGS', '\\Deleted')
                            except Exception as e:
                                logger.warning(f"Failed to mark email for deletion: {e}")
                        
                        # Add to processed set
                        self._processed_message_ids.add(email_message.message_id)
                        
                        # Add to processing queue
                        emails.append(email_message)
                        logger.debug(f"Queued email for processing: {email_message.subject}")
                    
                except Exception as e:
                    logger.error(f"Error processing email {msg_id}: {e}")
            
            # Expunge deleted messages
            if self.config.get('email.delete_after_print'):
                try:
                    self.imap_connection.expunge()
                except Exception as e:
                    logger.warning(f"Failed to expunge deleted messages: {e}")
            
            # Limit size of processed message IDs cache (keep last 1000)
            if len(self._processed_message_ids) > 1000:
                # Keep only 500 message IDs to prevent unbounded memory growth
                # Note: Sets are unordered in Python, so slicing the list doesn't
                # guarantee keeping the "most recent" IDs. However, this simple
                # approach is sufficient for preventing memory issues.
                # For production systems with high email volume, consider using
                # a collections.deque(maxlen=1000) or timestamp-based tracking
                # to ensure true LRU (Least Recently Used) behavior.
                recent_ids = list(self._processed_message_ids)[-500:]
                self._processed_message_ids = set(recent_ids)
            
            logger.info(f"Found {len(emails)} new emails to process")
            
        except Exception as e:
            logger.error(f"Error checking emails: {e}")
            # On serious errors, disconnect to force reconnection next time
            self.disconnect()
            
        return emails
    
    def _should_process_email(self, email_message: EmailMessage) -> bool:
        """
        Check if email should be processed based on filters
        
        Args:
            email_message: Email message to check
            
        Returns:
            True if email should be processed
        """
        # Check subject keywords
        subject_keywords = self.config.get('filters.subject_keywords', [])
        if subject_keywords:
            subject_lower = email_message.subject.lower()
            if not any(keyword.lower() in subject_lower for keyword in subject_keywords):
                logger.debug(f"Email filtered out by subject keywords: {email_message.subject}")
                return False
        
        # Check attachment size limits
        max_attachment_size = self.config.get('filters.max_attachment_size', 10485760)
        for attachment in email_message.attachments:
            if attachment['size'] > max_attachment_size:
                logger.warning(f"Email filtered out: attachment too large ({attachment['size']} bytes)")
                return False
        
        # Check allowed attachment types
        allowed_attachments = self.config.get('filters.allowed_attachments', [])
        if allowed_attachments:
            for attachment in email_message.attachments:
                filename = attachment['filename'].lower()
                if not any(filename.endswith(ext.lower()) for ext in allowed_attachments):
                    logger.warning(f"Email filtered out: disallowed attachment type ({filename})")
                    return False
        
        return True
    
    def run_check_loop(self, callback):
        """
        Run email checking loop
        
        Args:
            callback: Function to call with new emails
        """
        check_interval = self.config.get('email.check_interval', 30)
        
        logger.info(f"Starting email check loop (interval: {check_interval}s)")
        
        while True:
            try:
                new_emails = self.check_new_emails()
                if new_emails:
                    callback(new_emails)
                
                time.sleep(check_interval)
                
            except KeyboardInterrupt:
                logger.info("Email check loop interrupted")
                break
            except Exception as e:
                logger.error(f"Error in email check loop: {e}")
                time.sleep(check_interval)
        
        self.disconnect()