# Mail2printer Fixes and API - Implementation Summary

## Overview

This implementation addresses critical printing issues and adds a comprehensive REST API for Laravel integration.

## Problems Fixed

### 1. Duplicate Printing

**Root Cause:** Race condition where emails were marked as read AFTER being added to the processing queue, leading to re-processing if the service crashed or restarted.

**Solution:**
- Mark emails as read IMMEDIATELY before adding to processing queue
- Added Message-ID tracking with `_processed_message_ids` set
- Cache management to prevent unbounded memory growth (keeps last 500 IDs)

**Files Modified:**
- `mail2printer/email_handler.py`: Lines 165, 290-310

### 2. Printer Blocking at End of Page

**Root Cause:** Temporary files were deleted immediately after print job submission, before the printer finished reading them.

**Solution:**
- Changed `_print_file()` to return tuple `(job_id, success)` instead of just `bool`
- Added `wait_for_job_completion()` method to poll CUPS for job completion
- Added 2-5 second delays for non-CUPS systems
- Track active jobs in `_active_jobs` dictionary

**Files Modified:**
- `mail2printer/printer_manager.py`: Lines 60, 220-235, 255-290, 638-709, 844-879

### 3. Temporary File Deletion Race Conditions

**Root Cause:** Files were deleted immediately after print submission, but print spooling happens asynchronously.

**Solution:**
- Wait for job completion or fixed delay before cleanup
- Proper error handling for file deletion failures
- Changed attachment directory cleanup to use explicit `TemporaryDirectory()` management with try/finally

**Files Modified:**
- `mail2printer/printer_manager.py`: Print methods now wait before cleanup
- `mail2printer/service.py`: Lines 257-289 (attachment handling)

## New Features Added

### REST API for Laravel Integration

A complete Flask-based REST API with the following endpoints:

#### Status & Monitoring
- `GET /health` - Health check
- `GET /api/status` - Service status with configuration
- `GET /api/stats` - Detailed statistics with uptime
- `GET /api/printer/status` - Printer status and availability

#### Job Management
- `GET /api/printer/jobs` - List all print jobs
- `GET /api/printer/jobs/{id}` - Get specific job status
- `POST /api/printer/jobs/{id}/cancel` - Cancel a print job

#### Service Control
- `POST /api/service/restart` - Restart service (requires supervisor/systemd)
- `POST /api/service/stop` - Stop service gracefully

#### Security
- Optional API key authentication via `X-API-Key` header or query parameter
- Configurable in `config.yaml`

**Files Added:**
- `mail2printer/api.py` - Complete API implementation (330 lines)
- `docs/API.md` - Comprehensive API documentation (480+ lines)

**Files Modified:**
- `main.py` - Added API server threading and CLI options
- `config.yaml` - Added API configuration section
- `requirements.txt` - Added Flask dependency
- `README.md` - Updated with API features

## Technical Details

### New Methods Added

#### PrinterManager
```python
def wait_for_job_completion(job_id, timeout=30) -> bool
def get_all_jobs() -> Dict[int, Dict[str, Any]]
def get_printer_stats() -> Dict[str, Any]
```

#### Service
- Enhanced `_print_attachments()` with proper cleanup timing

#### EmailHandler
- Added `_processed_message_ids` set for duplicate detection
- Modified `check_new_emails()` to mark emails before processing

### Constants Added

**printer_manager.py:**
```python
JOB_STATE_PENDING = 3
JOB_STATE_HELD = 4
JOB_STATE_PROCESSING = 5
JOB_STATE_STOPPED = 6
JOB_STATE_CANCELED = 7
JOB_STATE_ABORTED = 8
JOB_STATE_COMPLETED = 9
```

**service.py:**
```python
BASE_WAIT_TIME = 5
WAIT_PER_ATTACHMENT = 2
MAX_WAIT_TIME = 30
```

## Testing

### Automated Tests
- All 26 existing unit tests pass
- Fixed test mock to return tuple instead of bool
- Test file: `tests/test_image_printing.py`

### Quick Test Script
- Created `test_quick.py` for rapid validation
- Tests imports, API routes, and configuration
- All tests passing

### Manual Testing Recommended
1. Test duplicate email prevention
2. Test print job completion with multiple attachments
3. Test API endpoints with curl or Postman
4. Test Laravel integration

## Configuration Changes

### New API Section in config.yaml

```yaml
api:
  enabled: true                # Enable/disable REST API
  host: "0.0.0.0"             # API server host (0.0.0.0 = all interfaces)
  port: 5000                   # API server port
  key: ""                      # API key for authentication (leave empty to disable)
  debug: false                 # Enable debug mode
```

## Usage Examples

### Start Service with API
```bash
python main.py --config config.yaml
```

### API Only Mode (No Email Processing)
```bash
python main.py --config config.yaml --api-only
```

### Disable API
```bash
python main.py --config config.yaml --no-api
```

### Test API
```bash
# Health check
curl http://localhost:5000/health

# Get status (with API key)
curl -H "X-API-Key: your-key" http://localhost:5000/api/status

# List jobs
curl -H "X-API-Key: your-key" http://localhost:5000/api/printer/jobs
```

## Laravel Integration Example

```php
<?php

namespace App\Services;

use Illuminate\Support\Facades\Http;

class Mail2PrinterService
{
    protected $baseUrl;
    protected $apiKey;

    public function __construct()
    {
        $this->baseUrl = config('mail2printer.base_url');
        $this->apiKey = config('mail2printer.api_key');
    }

    public function getPrinterStatus()
    {
        return Http::withHeaders(['X-API-Key' => $this->apiKey])
            ->get($this->baseUrl . '/api/printer/status')
            ->json();
    }

    public function cancelJob($jobId)
    {
        return Http::withHeaders(['X-API-Key' => $this->apiKey])
            ->post($this->baseUrl . "/api/printer/jobs/{$jobId}/cancel")
            ->json();
    }
}
```

## Production Deployment

### Important Notes
- **DO NOT** use Flask's built-in server in production
- Use Gunicorn, uWSGI, or similar WSGI server
- Deploy behind nginx for HTTPS and load balancing
- Always use API key authentication
- Monitor logs for unauthorized access

### Recommended Setup
```bash
# Install Gunicorn
pip install gunicorn

# Run with Gunicorn
gunicorn -w 4 -b 127.0.0.1:5000 'mail2printer.api:app'
```

## Code Quality Improvements

1. **Named Constants** - Replaced magic numbers with descriptive constants
2. **Type Hints** - Maintained type hints for better IDE support
3. **Error Handling** - Comprehensive error handling and logging
4. **Documentation** - Extensive inline comments and docstrings
5. **Security** - API key authentication and production warnings

## Dependencies Added

- **Flask** >= 2.0.0 - REST API framework

## Files Changed Summary

### Modified (6 files)
- `mail2printer/printer_manager.py` - Job tracking, completion waiting
- `mail2printer/email_handler.py` - Duplicate prevention
- `mail2printer/service.py` - Cleanup timing fixes
- `main.py` - API server integration
- `config.yaml` - API configuration
- `requirements.txt` - Flask dependency

### Added (3 files)
- `mail2printer/api.py` - REST API implementation
- `docs/API.md` - API documentation
- `test_quick.py` - Quick validation script

### Updated (1 file)
- `README.md` - Feature documentation

### Fixed (1 file)
- `tests/test_image_printing.py` - Mock return value

## Statistics

- **Lines Added**: ~1,500
- **Lines Modified**: ~150
- **New Methods**: 8
- **New Constants**: 12
- **Test Coverage**: All 26 tests passing
- **Documentation**: 2 new documents (480+ lines)

## Success Criteria Met

✅ Fixed duplicate printing issue  
✅ Fixed printer blocking at end of page  
✅ Fixed temporary file race conditions  
✅ Added Message-ID tracking  
✅ Created REST API with comprehensive endpoints  
✅ Added status and statistics monitoring  
✅ Added print job management  
✅ Added service control endpoints  
✅ Implemented API key authentication  
✅ Provided Laravel integration examples  
✅ All existing tests passing  
✅ Code review feedback addressed  
✅ Production deployment documentation  

## Next Steps

1. **Manual Testing**: Test the fixes with real email and printer
2. **Security Audit**: Review API key handling
3. **Performance Testing**: Test under load with multiple print jobs
4. **Documentation**: Add troubleshooting guide
5. **CI/CD**: Set up automated testing
6. **Monitoring**: Add metrics collection

## Support

For issues or questions:
- GitHub Issues: https://github.com/adaoss/Mail2printer/issues
- Documentation: `docs/` folder
- API Reference: `docs/API.md`
