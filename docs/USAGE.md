# Usage Guide

## Basic Usage

### Starting the Service
```bash
python main.py --config config.yaml
```

### Command Line Options
- `--config, -c`: Configuration file path (default: config.yaml)
- `--daemon, -d`: Run as daemon (background process)
- `--test-email`: Test email connection and exit
- `--test-printer`: Test printer connection and exit
- `--version`: Show version information

## Configuration

### Email Settings
```yaml
email:
  server: "imap.gmail.com"     # IMAP server
  port: 993                    # Server port
  use_ssl: true               # Use SSL encryption
  username: "user@gmail.com"   # Email address
  password: "app_password"     # Password or app password
  inbox_folder: "INBOX"        # Folder to monitor
  check_interval: 30           # Check frequency (seconds)
  mark_as_read: true          # Mark processed emails as read
  delete_after_print: false   # Delete emails after printing
```

### Printer Settings
```yaml
printer:
  name: "default"             # Printer name
  paper_size: "A4"           # Paper size
  orientation: "portrait"     # Page orientation
  quality: "draft"           # Print quality
  duplex: false              # Two-sided printing
  color: true                # Color printing
```

### Email Filtering
```yaml
filters:
  allowed_senders:           # Only process emails from these addresses
    - "boss@company.com"
    - "important@client.com"
  
  blocked_senders:           # Never process emails from these addresses
    - "spam@example.com"
    - "noreply@marketing.com"
  
  subject_keywords:          # Only process emails with these keywords
    - "PRINT"
    - "URGENT"
    - "INVOICE"
  
  max_attachment_size: 10485760  # 10MB limit
  
  allowed_attachments:       # Allowed file types
    - ".pdf"
    - ".docx"
    - ".jpg"
    - ".png"
```

## Features

### Email Content Processing
- **Plain Text**: Emails are printed with proper formatting
- **HTML Content**: Converted to PDF for better printing
- **Mixed Content**: HTML is preferred over plain text when both are available

### Attachment Handling
- Automatically extracts and prints supported attachments
- File type validation based on configuration
- Size limits to prevent large file processing
- Temporary file cleanup after printing

### Security Features
- Sender whitelist/blacklist
- Domain filtering
- Content keyword filtering
- File type restrictions
- Size limitations

## Monitoring and Logging

### Log Levels
```yaml
logging:
  level: "INFO"              # DEBUG, INFO, WARNING, ERROR
  file: "mail2printer.log"   # Log file location
```

### Log Messages
- Service startup/shutdown
- Email processing status
- Print job results
- Error conditions
- Statistics

### Statistics
The service tracks:
- Total emails processed
- Emails successfully printed
- Failed print jobs
- Service uptime

## Common Use Cases

### 1. Home Office Printing
```yaml
# Simple home setup
email:
  username: "home@gmail.com"
  password: "app_password"
  check_interval: 60

printer:
  name: "Home-Printer"
  quality: "normal"

filters:
  subject_keywords: ["PRINT"]
```

### 2. Business Document Processing
```yaml
# Business environment with restrictions
filters:
  allowed_senders:
    - "accounting@company.com"
    - "orders@supplier.com"
  
  allowed_attachments:
    - ".pdf"
    - ".docx"
  
  max_attachment_size: 5242880  # 5MB limit

processing:
  max_pages_per_document: 20
```

### 3. Receipt Printing
```yaml
# For receipt/ticket printing
printer:
  name: "Receipt-Printer"
  paper_size: "Custom.80x200mm"
  quality: "draft"

filters:
  subject_keywords: ["RECEIPT", "TICKET"]
  
processing:
  convert_html_to_pdf: false  # For thermal printers
```

## Troubleshooting

### Email Issues
1. **Authentication Failures**
   - Use app passwords for Gmail/Yahoo
   - Check 2FA settings
   - Verify server settings

2. **No New Emails Detected**
   - Check folder name (INBOX vs Inbox)
   - Verify email filters
   - Test with --test-email

### Printing Issues
1. **Printer Not Found**
   - List printers: `lpstat -p`
   - Check CUPS status: `systemctl status cups`
   - Use exact printer name

2. **Print Quality Issues**
   - Adjust quality settings
   - Check paper size configuration
   - Test with simple document

### Performance Issues
1. **High Memory Usage**
   - Reduce max_attachment_size
   - Enable delete_after_print
   - Limit max_pages_per_document

2. **Slow Processing**
   - Increase check_interval
   - Optimize email filters
   - Use draft print quality

## Security Best Practices

1. **Email Security**
   - Use app passwords
   - Enable sender filtering
   - Regular password rotation

2. **System Security**
   - Run with limited user privileges
   - Secure configuration file permissions (chmod 600)
   - Monitor logs regularly

3. **Network Security**
   - Use SSL/TLS connections
   - Consider VPN for email access
   - Firewall configuration

## Integration Examples

### Systemd Service
Create `/etc/systemd/system/mail2printer.service`:
```ini
[Unit]
Description=Mail2printer Service
After=network.target

[Service]
Type=simple
User=mail2printer
WorkingDirectory=/opt/mail2printer
ExecStart=/usr/bin/python3 main.py --config /etc/mail2printer/config.yaml
Restart=always

[Install]
WantedBy=multi-user.target
```

### Docker Container
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

CMD ["python", "main.py", "--config", "config.yaml"]
```

### Cron Job (Alternative)
```bash
# Check every 5 minutes
*/5 * * * * /usr/bin/python3 /opt/mail2printer/main.py --config /etc/mail2printer/config.yaml
```