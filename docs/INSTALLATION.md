# Installation Guide

## Prerequisites

### System Requirements
- Python 3.8 or higher
- CUPS printing system (Linux/macOS) or Windows printing service
- Internet connection for email access

### Dependencies
- PyYAML for configuration file handling
- pycups for CUPS integration (Linux/macOS)
- wkhtmltopdf for HTML to PDF conversion (optional but recommended)
- weasyprint for HTML to PDF conversion (alternative to wkhtmltopdf)

## Installation Steps

### 1. Clone the Repository
```bash
git clone https://github.com/adaoss/Mail2printer.git
cd Mail2printer
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3. Install System Dependencies

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install python3-cups wkhtmltopdf
```

#### CentOS/RHEL/Fedora
```bash
sudo yum install python3-pycups wkhtmltopdf
# or for newer versions:
sudo dnf install python3-pycups wkhtmltopdf
```

#### macOS
```bash
brew install cups
brew install --cask wkhtmltopdf
```

### 4. Configure the Service
1. Copy the example configuration:
   ```bash
   cp config.yaml my_config.yaml
   ```

2. Edit `my_config.yaml` with your email and printer settings:
   ```yaml
   email:
     username: "your-email@example.com"
     password: "your-app-password"
     server: "imap.gmail.com"
   
   printer:
     name: "your-printer-name"
   ```

### 5. Test the Installation
```bash
# Test email connection
python main.py --config my_config.yaml --test-email

# Test printer connection
python main.py --config my_config.yaml --test-printer
```

## Email Provider Setup

### Gmail
1. Enable 2-factor authentication
2. Generate an app password
3. Use the app password in the configuration

### Outlook/Hotmail
```yaml
email:
  server: "outlook.office365.com"
  port: 993
```

### Yahoo Mail
```yaml
email:
  server: "imap.mail.yahoo.com"
  port: 993
```

## Printer Setup

### Finding Your Printer Name
```bash
# List available printers
lpstat -p

# Get default printer
lpstat -d
```

### Common Printer Settings
```yaml
printer:
  name: "HP-LaserJet-P1102"  # Use actual printer name
  paper_size: "A4"           # or "Letter" for US
  quality: "normal"          # draft, normal, high
  duplex: true              # Enable two-sided printing
```

## Running the Service

### Interactive Mode
```bash
python main.py --config my_config.yaml
```

### Daemon Mode (Linux/macOS only)
```bash
python main.py --config my_config.yaml --daemon
```

### As a System Service
See [SERVICE.md](SERVICE.md) for systemd service configuration.

## Troubleshooting

### Email Connection Issues
- Verify email credentials
- Check firewall settings
- Enable "less secure apps" if required by email provider
- Use app passwords for Gmail/Yahoo

### Printer Issues
- Ensure CUPS service is running: `systemctl status cups`
- Check printer status: `lpstat -p`
- Test printing: `echo "test" | lp -d your-printer`

### Permission Issues
- Add user to `lp` group: `sudo usermod -a -G lp username`
- Check file permissions in working directory

## Security Considerations

1. **Email Credentials**: Use app passwords instead of main passwords
2. **Configuration File**: Protect with appropriate file permissions (600)
3. **Network**: Consider using VPN for email access
4. **Filtering**: Configure sender and content filters to prevent abuse

## Next Steps

- Configure email filters in `config.yaml`
- Set up logging and monitoring
- Create systemd service for automatic startup
- Test with various email formats and attachments