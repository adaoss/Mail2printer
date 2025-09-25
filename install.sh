#!/bin/bash
# Mail2printer Installation Script

set -e

echo "Mail2printer Installation Script"
echo "================================"

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "This script should not be run as root for security reasons."
   exit 1
fi

# Check Python version
echo "Checking Python version..."
if ! python3 -c "import sys; assert sys.version_info >= (3, 8)" 2>/dev/null; then
    echo "Error: Python 3.8 or higher is required"
    exit 1
fi
echo "✓ Python version check passed"

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install --user -r requirements.txt
echo "✓ Python dependencies installed"

# Check system dependencies
echo "Checking system dependencies..."

# Check for CUPS
if command -v lpstat &> /dev/null; then
    echo "✓ CUPS found"
else
    echo "⚠ CUPS not found - printing may not work"
    echo "  Install with: sudo apt-get install cups"
fi

# Check for wkhtmltopdf
if command -v wkhtmltopdf &> /dev/null; then
    echo "✓ wkhtmltopdf found"
else
    echo "⚠ wkhtmltopdf not found - HTML to PDF conversion will use fallback"
    echo "  Install with: sudo apt-get install wkhtmltopdf"
fi

# Create configuration file if it doesn't exist
if [ ! -f "my_config.yaml" ]; then
    echo "Creating configuration file..."
    cp config.yaml my_config.yaml
    echo "✓ Configuration file created: my_config.yaml"
    echo "  Please edit this file with your email and printer settings"
else
    echo "✓ Configuration file already exists: my_config.yaml"
fi

# Test basic functionality
echo "Testing basic functionality..."
if python3 main.py --version > /dev/null 2>&1; then
    echo "✓ Basic functionality test passed"
else
    echo "✗ Basic functionality test failed"
    exit 1
fi

echo ""
echo "Installation completed successfully!"
echo ""
echo "Next steps:"
echo "1. Edit my_config.yaml with your email and printer settings"
echo "2. Test email connection: python3 main.py --config my_config.yaml --test-email"
echo "3. Test printer connection: python3 main.py --config my_config.yaml --test-printer"
echo "4. Run the service: python3 main.py --config my_config.yaml"
echo ""
echo "For more information, see docs/INSTALLATION.md"