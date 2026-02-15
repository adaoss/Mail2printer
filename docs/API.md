# Mail2printer REST API Documentation

## Overview

The Mail2printer REST API provides endpoints for Laravel applications (or any HTTP client) to interact with the Mail2printer service. You can monitor status, manage print jobs, and control the service.

## Base URL

```
http://localhost:5000/api
```

## Authentication

The API supports optional API key authentication. If an API key is configured in `config.yaml`, all API requests must include the key either:

- In the `X-API-Key` HTTP header
- As a query parameter: `?api_key=YOUR_KEY`

Example with header:
```bash
curl -H "X-API-Key: your-secret-key" http://localhost:5000/api/status
```

Example with query parameter:
```bash
curl http://localhost:5000/api/status?api_key=your-secret-key
```

## Endpoints

### Health Check

**GET** `/health`

Check if the API server is running.

**Response:**
```json
{
  "status": "ok",
  "service": "mail2printer",
  "version": "1.0.0"
}
```

### Service Status

**GET** `/api/status`

Get current service status including configuration and running state.

**Response:**
```json
{
  "success": true,
  "data": {
    "running": true,
    "stats": {
      "emails_processed": 42,
      "emails_printed": 40,
      "print_jobs_failed": 2,
      "service_start_time": 1645123456.789
    },
    "config": {
      "email_server": "imap.gmail.com",
      "printer": "HP_LaserJet",
      "check_interval": 30
    }
  }
}
```

### Service Statistics

**GET** `/api/stats`

Get detailed service statistics including uptime.

**Response:**
```json
{
  "success": true,
  "data": {
    "emails_processed": 42,
    "emails_printed": 40,
    "print_jobs_failed": 2,
    "service_start_time": 1645123456.789,
    "uptime_seconds": 3600,
    "uptime_formatted": "1h 0m"
  }
}
```

### Printer Status

**GET** `/api/printer/status`

Get printer status and statistics.

**Response:**
```json
{
  "success": true,
  "data": {
    "printer_name": "HP_LaserJet",
    "available_printers": ["HP_LaserJet", "Canon_Printer"],
    "active_jobs": 2,
    "cups_available": true,
    "queued_jobs": 3,
    "job_ids": [101, 102, 103],
    "online": true
  }
}
```

### List Print Jobs

**GET** `/api/printer/jobs`

List all current print jobs in the queue.

**Response:**
```json
{
  "success": true,
  "data": {
    "jobs": [
      {
        "job_id": 101,
        "info": {
          "job-name": "Email: Invoice",
          "job-state": 5,
          "job-printer-uri": "ipp://localhost/printers/HP_LaserJet"
        }
      },
      {
        "job_id": 102,
        "info": {
          "job-name": "Attachment: report.pdf",
          "job-state": 3,
          "job-printer-uri": "ipp://localhost/printers/HP_LaserJet"
        }
      }
    ],
    "count": 2
  }
}
```

**Job States:**
- 3: Pending
- 4: Held
- 5: Processing
- 6: Stopped
- 7: Canceled
- 8: Aborted
- 9: Completed

### Get Job Status

**GET** `/api/printer/jobs/{job_id}`

Get the status of a specific print job.

**Parameters:**
- `job_id` (integer): The print job ID

**Response:**
```json
{
  "success": true,
  "data": {
    "job_id": 101,
    "status": "5"
  }
}
```

### Cancel Print Job

**POST** `/api/printer/jobs/{job_id}/cancel`  
**DELETE** `/api/printer/jobs/{job_id}/cancel`

Cancel a specific print job.

**Parameters:**
- `job_id` (integer): The print job ID to cancel

**Response:**
```json
{
  "success": true,
  "message": "Job 101 cancelled successfully"
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "Failed to cancel job 101"
}
```

### Restart Service

**POST** `/api/service/restart`

Request a service restart (requires supervisor or systemd management).

**Response:**
```json
{
  "success": true,
  "message": "Service restart requested",
  "pid": 12345
}
```

### Stop Service

**POST** `/api/service/stop`

Stop the Mail2printer service gracefully.

**Response:**
```json
{
  "success": true,
  "message": "Service stopped"
}
```

## Error Responses

All endpoints may return error responses in the following format:

**401 Unauthorized** (Invalid API key):
```json
{
  "error": "Unauthorized",
  "message": "Valid API key required"
}
```

**404 Not Found**:
```json
{
  "error": "Not found",
  "message": "The requested endpoint does not exist"
}
```

**500 Internal Server Error**:
```json
{
  "success": false,
  "error": "Error message here"
}
```

**503 Service Unavailable**:
```json
{
  "error": "Service not initialized"
}
```

## Laravel Integration Example

### 1. Create a Service Class

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
        $this->baseUrl = config('mail2printer.base_url', 'http://localhost:5000');
        $this->apiKey = config('mail2printer.api_key');
    }

    protected function request($method, $endpoint, $data = [])
    {
        $url = $this->baseUrl . $endpoint;
        
        $request = Http::withHeaders([
            'X-API-Key' => $this->apiKey,
        ]);

        return $request->$method($url, $data);
    }

    public function getStatus()
    {
        return $this->request('get', '/api/status')->json();
    }

    public function getStats()
    {
        return $this->request('get', '/api/stats')->json();
    }

    public function getPrinterStatus()
    {
        return $this->request('get', '/api/printer/status')->json();
    }

    public function listJobs()
    {
        return $this->request('get', '/api/printer/jobs')->json();
    }

    public function cancelJob($jobId)
    {
        return $this->request('post', "/api/printer/jobs/{$jobId}/cancel")->json();
    }

    public function restartService()
    {
        return $this->request('post', '/api/service/restart')->json();
    }
}
```

### 2. Add Configuration

Create `config/mail2printer.php`:

```php
<?php

return [
    'base_url' => env('MAIL2PRINTER_URL', 'http://localhost:5000'),
    'api_key' => env('MAIL2PRINTER_API_KEY', ''),
];
```

Add to `.env`:

```
MAIL2PRINTER_URL=http://localhost:5000
MAIL2PRINTER_API_KEY=your-secret-key
```

### 3. Use in Controller

```php
<?php

namespace App\Http\Controllers;

use App\Services\Mail2PrinterService;

class PrinterController extends Controller
{
    protected $printer;

    public function __construct(Mail2PrinterService $printer)
    {
        $this->printer = $printer;
    }

    public function status()
    {
        $status = $this->printer->getPrinterStatus();
        return view('printer.status', compact('status'));
    }

    public function jobs()
    {
        $jobs = $this->printer->listJobs();
        return view('printer.jobs', compact('jobs'));
    }

    public function cancelJob($id)
    {
        $result = $this->printer->cancelJob($id);
        
        if ($result['success']) {
            return redirect()->back()->with('success', 'Job cancelled');
        }
        
        return redirect()->back()->with('error', 'Failed to cancel job');
    }
}
```

## Configuration

To enable the API, configure in `config.yaml`:

```yaml
api:
  enabled: true                # Enable/disable REST API
  host: "0.0.0.0"             # Listen on all interfaces
  port: 5000                   # API server port
  key: "your-secret-key-here" # API key (leave empty to disable auth)
  debug: false                 # Debug mode
```

## Running the Service

### With API (default):
```bash
python main.py --config config.yaml
```

### Without API:
```bash
python main.py --config config.yaml --no-api
```

### API Only (no email processing):
```bash
python main.py --config config.yaml --api-only
```

## Security Recommendations

1. **Always use an API key** in production environments
2. **Use HTTPS** when exposing the API over a network (use a reverse proxy like nginx)
3. **Firewall rules** - restrict API access to trusted networks/IPs
4. **Monitor logs** for unauthorized access attempts
5. **Rotate API keys** regularly

## Troubleshooting

### API Not Responding

1. Check if the API is enabled in config:
   ```yaml
   api:
     enabled: true
   ```

2. Check if the port is already in use:
   ```bash
   netstat -tuln | grep 5000
   ```

3. Check firewall rules:
   ```bash
   sudo ufw status
   ```

### 401 Unauthorized

- Verify the API key matches in both client and server configuration
- Check that the key is being sent correctly (header or query param)

### 503 Service Unavailable

- Service may not be fully initialized yet
- Check service logs for startup errors

## Support

For issues and questions:
- GitHub Issues: https://github.com/adaoss/Mail2printer/issues
- Documentation: See `docs/` folder
