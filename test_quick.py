#!/usr/bin/env python3
"""
Quick test script to verify Mail2printer functionality
Tests basic imports and API endpoints (without requiring actual printer/email)
"""

import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Testing Mail2printer imports...")

# Test basic imports
try:
    from mail2printer.config import Config
    print("✓ Config module imports successfully")
except Exception as e:
    print(f"✗ Config import failed: {e}")
    sys.exit(1)

try:
    from mail2printer.printer_manager import PrinterManager
    print("✓ PrinterManager module imports successfully")
except Exception as e:
    print(f"✗ PrinterManager import failed: {e}")
    sys.exit(1)

try:
    from mail2printer.email_handler import EmailHandler
    print("✓ EmailHandler module imports successfully")
except Exception as e:
    print(f"✗ EmailHandler import failed: {e}")
    sys.exit(1)

try:
    from mail2printer.service import Mail2PrinterService
    print("✓ Service module imports successfully")
except Exception as e:
    print(f"✗ Service import failed: {e}")
    sys.exit(1)

try:
    from mail2printer import api
    print("✓ API module imports successfully")
except Exception as e:
    print(f"✗ API import failed: {e}")
    sys.exit(1)

print("\nTesting API routes...")

# Test API routes are defined
try:
    app = api.app
    routes = [str(rule) for rule in app.url_map.iter_rules()]
    
    expected_routes = [
        '/health',
        '/api/status',
        '/api/stats',
        '/api/printer/status',
        '/api/printer/jobs',
        '/api/printer/jobs/<int:job_id>',
        '/api/printer/jobs/<int:job_id>/cancel',
        '/api/service/restart',
        '/api/service/stop'
    ]
    
    for route in expected_routes:
        if any(route in r for r in routes):
            print(f"✓ Route {route} is defined")
        else:
            print(f"✗ Route {route} is missing")
            sys.exit(1)
    
    print(f"\n✓ All {len(expected_routes)} expected API routes are defined")
    
except Exception as e:
    print(f"✗ API route check failed: {e}")
    sys.exit(1)

print("\nTesting configuration...")

# Test config loading
try:
    import tempfile
    import yaml
    
    # Create a minimal test config
    test_config = {
        'email': {
            'server': 'test.example.com',
            'port': 993,
            'username': 'test@example.com',
            'password': 'test123'
        },
        'printer': {
            'name': 'test_printer'
        },
        'api': {
            'enabled': True,
            'port': 5000,
            'key': 'test-key-123'
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(test_config, f)
        config_path = f.name
    
    try:
        config = Config(config_path)
        
        # Test config access
        assert config.get('email.server') == 'test.example.com', "Config email.server mismatch"
        assert config.get('printer.name') == 'test_printer', "Config printer.name mismatch"
        assert config.get('api.enabled') is True, "Config api.enabled mismatch"
        assert config.get('api.key') == 'test-key-123', "Config api.key mismatch"
        
        print("✓ Configuration loading works correctly")
        print("✓ Configuration value access works correctly")
        
    finally:
        os.unlink(config_path)
        
except Exception as e:
    print(f"✗ Configuration test failed: {e}")
    sys.exit(1)

print("\n" + "="*50)
print("✓ All tests passed!")
print("="*50)
print("\nMail2printer is ready to use.")
print("\nNext steps:")
print("1. Configure your email and printer settings in config.yaml")
print("2. Test connections: python main.py --test-email --test-printer")
print("3. Start the service: python main.py")
print("4. Access the API at http://localhost:5000/health")
