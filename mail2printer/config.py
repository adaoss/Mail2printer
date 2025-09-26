"""
Configuration management for Mail2printer service
"""

import os
import yaml
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class Config:
    """Configuration manager for Mail2printer service"""
    
    DEFAULT_CONFIG = {
        'email': {
            'server': 'imap.gmail.com',
            'port': 993,
            'use_ssl': True,
            'username': '',
            'password': '',
            'inbox_folder': 'INBOX',
            'check_interval': 30,
            'mark_as_read': True,
            'delete_after_print': False
        },
        'printer': {
            'name': 'default',
            'paper_size': 'A4',
            'orientation': 'portrait',
            'quality': 'draft',
            'duplex': False,
            'color': True
        },
        'filters': {
            'allowed_senders': [],
            'blocked_senders': [],
            'subject_keywords': [],
            'max_attachment_size': 10485760,  # 10MB
            'allowed_attachments': ['.pdf', '.txt', '.doc', '.docx', '.jpg', '.png']
        },
        'processing': {
            'print_text_emails': True,
            'print_html_emails': True,
            'print_attachments': True,
            'convert_html_to_pdf': True,
            'max_pages_per_document': 50
        },
        'logging': {
            'level': 'INFO',
            'file': 'mail2printer.log',
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        },
        'security': {
            'require_authentication': False,
            'allowed_domains': [],
            'encryption_key': None
        }
    }
    
    def __init__(self, config_path: str = 'config.yaml'):
        """
        Initialize configuration
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = Path(config_path)
        self.data = self.DEFAULT_CONFIG.copy()
        self.load()
    
    def load(self):
        """Load configuration from file"""
        if not self.config_path.exists():
            logger.warning(f"Configuration file {self.config_path} not found, using defaults")
            self.save()  # Create default config file
            return
        
        try:
            with open(self.config_path, 'r') as f:
                if self.config_path.suffix.lower() == '.json':
                    loaded_config = json.load(f)
                else:
                    loaded_config = yaml.safe_load(f)
            
            # Merge with defaults (recursive merge)
            self.data = self._merge_configs(self.DEFAULT_CONFIG, loaded_config)
            logger.info(f"Configuration loaded from {self.config_path}")
            
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            raise
    
    def save(self):
        """Save current configuration to file"""
        try:
            with open(self.config_path, 'w') as f:
                if self.config_path.suffix.lower() == '.json':
                    json.dump(self.data, f, indent=2)
                else:
                    yaml.dump(self.data, f, default_flow_style=False, indent=2)
            
            logger.info(f"Configuration saved to {self.config_path}")
            
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            raise
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation
        
        Args:
            key: Configuration key (e.g., 'email.server')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self.data
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """
        Set configuration value using dot notation
        
        Args:
            key: Configuration key (e.g., 'email.server')
            value: Value to set
        """
        keys = key.split('.')
        config = self.data
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def _merge_configs(self, default: Dict, loaded: Dict) -> Dict:
        """
        Recursively merge loaded config with defaults
        
        Args:
            default: Default configuration
            loaded: Loaded configuration
            
        Returns:
            Merged configuration
        """
        result = default.copy()
        
        for key, value in loaded.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def validate(self) -> bool:
        """
        Validate configuration
        
        Returns:
            True if configuration is valid
        """
        errors = []
        
        # Validate email settings
        if not self.get('email.username'):
            errors.append("Email username is required")
        
        if not self.get('email.password'):
            errors.append("Email password is required")
        
        if self.get('email.port') <= 0:
            errors.append("Email port must be positive")
        
        # Validate printer settings - only require printer name if it's not 'default'
        printer_name = self.get('printer.name')
        if not printer_name or (printer_name.strip() == ''):
            errors.append("Printer name cannot be empty")
        
        # Log validation errors
        for error in errors:
            logger.error(f"Configuration validation error: {error}")
        
        return len(errors) == 0