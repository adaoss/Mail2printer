# Mail2printer

A Python service that automatically prints incoming emails and their attachments. Perfect for home offices, businesses, and any scenario where you need physical copies of important emails.

## Features

### 📧 Email Processing
- **IMAP Support**: Works with Gmail, Outlook, Yahoo, and other IMAP providers
- **Content Types**: Handles plain text and HTML emails
- **Attachment Support**: Prints PDF, Word documents, images, and more
- **Smart Filtering**: Filter by sender, subject keywords, and file types

### 🖨️ Printing Capabilities  
- **CUPS Integration**: Native support for Linux/macOS printing
- **Multiple Formats**: Text, HTML-to-PDF conversion, and direct file printing
- **Print Options**: Paper size, quality, duplex, color settings
- **Page Limits**: Prevent excessive printing with configurable limits

### 🔒 Security & Filtering
- **Sender Whitelist/Blacklist**: Control who can trigger printing
- **Domain Filtering**: Restrict to specific email domains
- **File Type Validation**: Only print approved attachment types
- **Size Limits**: Prevent large file processing

### 📊 Monitoring & Logging
- **Comprehensive Logging**: Track all email processing and print jobs
- **Statistics**: Monitor service performance and success rates
- **Health Checks**: Built-in connection testing for email and printer

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
- **[HP Printer Fix](docs/HP_PRINTER_FIX.md)** - Fix for HP SmartTank 555 blocking issues
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

## Security Considerations

- Use app passwords instead of main email passwords
- Configure sender filtering to prevent abuse  
- Set appropriate file permissions (600) on config files
- Monitor logs for unauthorized access attempts
- Consider running as dedicated service user

## Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Troubleshooting

### HP Printers (SmartTank 555, etc.)

If you experience blocking or hanging at the end of page printing:
- See **[HP Printer Fix Documentation](docs/HP_PRINTER_FIX.md)** for detailed solution
- Ensure `wait_for_completion: true` is set in your configuration
- Adjust `job_timeout` if needed (default: 300 seconds)

### Other Issues

For general troubleshooting:
- Check printer connection: `python main.py --config my_config.yaml --test-printer`
- Check email connection: `python main.py --config my_config.yaml --test-email`
- Review logs in `mail2printer.log`
- Verify CUPS status: `lpstat -t`

## Support

For support, please:
1. Check the documentation in the `docs/` folder
2. Review example configurations in `examples/`
3. Search existing issues on GitHub
4. Create a new issue with detailed information

---

**Made with ❤️ for the Mail2printer community**
