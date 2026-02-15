# Mail2printer

A Python service that automatically prints incoming emails and their attachments. Perfect for home offices, businesses, and any scenario where you need physical copies of important emails.

## Features

### 📧 Email Processing
- **IMAP Support**: Works with Gmail, Outlook, Yahoo, and other IMAP providers
- **Content Types**: Handles plain text and HTML emails
- **Attachment Support**: Prints PDF, Word documents, images, and more
- **Smart Filtering**: Filter by sender, subject keywords, and file types
- **Duplicate Prevention**: Prevents the same email from being printed multiple times

### 🖨️ Printing Capabilities  
- **CUPS Integration**: Native support for Linux/macOS printing
- **Multiple Formats**: Text, HTML-to-PDF conversion, and direct file printing
- **Print Options**: Paper size, quality, duplex, color settings
- **Page Limits**: Prevent excessive printing with configurable limits
- **Job Management**: Track and cancel print jobs

### 🌐 REST API
- **Laravel Integration**: Ready-to-use REST API for Laravel applications
- **Status Monitoring**: Get real-time service and printer status
- **Job Control**: List, monitor, and cancel print jobs remotely
- **Statistics**: Access service statistics and uptime
- **Secure Authentication**: Optional API key authentication

### 🔒 Security & Filtering
- **Sender Whitelist/Blacklist**: Control who can trigger printing
- **Domain Filtering**: Restrict to specific email domains
- **File Type Validation**: Only print approved attachment types
- **Size Limits**: Prevent large file processing
- **API Security**: Optional API key protection for remote access

### 📊 Monitoring & Logging
- **Comprehensive Logging**: Track all email processing and print jobs
- **Statistics**: Monitor service performance and success rates
- **Health Checks**: Built-in connection testing for email and printer
- **REST API**: Monitor and control the service remotely

## Quick Start

### 1. Installation
```bash
git clone https://github.com/adaoss/Mail2printer.git
cd Mail2printer
pip install -r requirements.txt
```

### 2. Configuration
```bash
cp config.yaml my_config.yaml
# Edit my_config.yaml with your email and printer settings
```

### 3. Test Connections
```bash
python main.py --config my_config.yaml --test-email
python main.py --config my_config.yaml --test-printer
```

### 4. Run the Service
```bash
python main.py --config my_config.yaml
```

## Configuration Example

```yaml
email:
  server: "imap.gmail.com"
  port: 993
  username: "your-email@gmail.com"
  password: "your-app-password"
  check_interval: 30

printer:
  name: "default"
  paper_size: "A4"
  quality: "normal"

filters:
  subject_keywords: ["PRINT"]  # Only print emails with "PRINT" in subject
  allowed_attachments: [".pdf", ".docx", ".jpg"]
```

## Use Cases

### 🏠 Home Office
- Print important emails and documents automatically
- Receipt printing from online purchases
- Family photo printing from email attachments

### 🏢 Business Environment
- Invoice and purchase order processing
- Document workflow automation
- Remote printing for traveling employees

### 🎫 Service Integration
- Ticket printing from booking confirmations
- Label printing for shipping
- Report generation and distribution

## Documentation

- **[Installation Guide](docs/INSTALLATION.md)** - Detailed setup instructions
- **[Usage Guide](docs/USAGE.md)** - Configuration and operation
- **[API Documentation](docs/API.md)** - REST API reference for Laravel integration
- **[Examples](examples/)** - Ready-to-use configuration files

## Requirements

- Python 3.8+
- CUPS (Linux/macOS) or Windows Print Service
- Email account with IMAP access
- Network printer or local printer

### Python Dependencies
- PyYAML - Configuration file handling
- pycups - CUPS integration (optional but recommended)
- weasyprint - HTML to PDF conversion (optional)
- Flask - REST API server (optional, for API features)

## API Usage

Mail2printer includes a REST API for integration with Laravel or other applications. Enable the API in your configuration:

```yaml
api:
  enabled: true
  host: "0.0.0.0"
  port: 5000
  key: "your-secret-key"
```

Then access endpoints like:
- `GET /api/status` - Get service status
- `GET /api/printer/status` - Get printer status
- `GET /api/printer/jobs` - List print jobs
- `POST /api/printer/jobs/{id}/cancel` - Cancel a job

See **[API Documentation](docs/API.md)** for complete API reference and Laravel integration examples.

## Security Considerations

- Use app passwords instead of main email passwords
- Configure sender filtering to prevent abuse  
- Set appropriate file permissions (600) on config files
- Monitor logs for unauthorized access attempts
- Consider running as dedicated service user
- **Use API key authentication** when enabling the REST API
- **Use HTTPS/reverse proxy** when exposing API over network

## Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please:
1. Check the documentation in the `docs/` folder
2. Review example configurations in `examples/`
3. Search existing issues on GitHub
4. Create a new issue with detailed information

---

**Made with ❤️ for the Mail2printer community**
