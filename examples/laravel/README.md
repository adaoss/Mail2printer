# Laravel Integration Examples

This directory contains example code for integrating Mail2printer with Laravel applications.

## Files

- **Mail2PrinterController.php** - Example Laravel controller with all API endpoints
- **routes.php** - Example routes configuration
- **README.md** - This file

## Setup Instructions

### 1. Install HTTP Client (if needed)

Laravel 7+ includes HTTP client by default. For older versions:

```bash
composer require guzzlehttp/guzzle
```

### 2. Configure Environment

Add to your `.env` file:

```env
MAIL2PRINTER_URL=http://localhost:5000
MAIL2PRINTER_API_KEY=your-secret-api-key
```

### 3. Configure Services

Add to `config/services.php`:

```php
'mail2printer' => [
    'url' => env('MAIL2PRINTER_URL', 'http://localhost:5000'),
    'api_key' => env('MAIL2PRINTER_API_KEY'),
],
```

### 4. Copy Controller

Copy `Mail2PrinterController.php` to `app/Http/Controllers/`

### 5. Add Routes

Add the routes from `routes.php` to your `routes/web.php`

### 6. Create Views (Optional)

Create views in `resources/views/mail2printer/`:

- `dashboard.blade.php` - Main dashboard
- `jobs.blade.php` - List print jobs
- `statistics.blade.php` - Show statistics

## Usage Examples

### In a Controller

```php
use Illuminate\Support\Facades\Http;

class MyController extends Controller
{
    public function printStatus()
    {
        $response = Http::withHeaders([
            'X-API-Key' => config('services.mail2printer.api_key')
        ])->get(config('services.mail2printer.url') . '/api/status');
        
        return $response->json();
    }
}
```

### In a Blade Template

```blade
@if($printerStatus['data']['online'])
    <span class="badge badge-success">Online</span>
@else
    <span class="badge badge-danger">Offline</span>
@endif

<p>Queued Jobs: {{ $printerStatus['data']['queued_jobs'] }}</p>
```

### AJAX Request

```javascript
fetch('/printer/jobs/123', {
    headers: {
        'X-Requested-With': 'XMLHttpRequest',
        'Accept': 'application/json'
    }
})
.then(response => response.json())
.then(data => {
    console.log('Job Status:', data.status);
});
```

## Available Routes

When using the example routes:

- `GET /printer` - Dashboard
- `GET /printer/jobs` - List jobs
- `GET /printer/jobs/{id}` - Job status
- `POST /printer/jobs/{id}/cancel` - Cancel job
- `GET /printer/statistics` - Statistics
- `POST /printer/restart` - Restart service
- `GET /printer/health` - Health check

## API Endpoints

The controller wraps these Mail2printer API endpoints:

- `GET /health` - Health check
- `GET /api/status` - Service status
- `GET /api/stats` - Statistics
- `GET /api/printer/status` - Printer status
- `GET /api/printer/jobs` - List jobs
- `GET /api/printer/jobs/{id}` - Job status
- `POST /api/printer/jobs/{id}/cancel` - Cancel job
- `POST /api/service/restart` - Restart service

## Security Notes

1. **Always protect routes** with authentication middleware
2. **Use HTTPS** in production
3. **Validate input** before sending to API
4. **Handle errors gracefully** - API might be unavailable
5. **Rate limit** API calls to prevent abuse

## Error Handling

The controller includes basic error handling. Enhance it based on your needs:

```php
protected function apiRequest($method, $endpoint, $data = [])
{
    try {
        // ... API call
        
        if (!$response->successful()) {
            // Log the error
            Log::error('Mail2printer API error', [
                'status' => $response->status(),
                'body' => $response->body()
            ]);
            
            // You might want to throw an exception
            // or return a default value
            return null;
        }
        
        return $response->json();
        
    } catch (\Exception $e) {
        // Handle connection errors
        Log::error('Mail2printer connection error', [
            'message' => $e->getMessage()
        ]);
        
        return null;
    }
}
```

## Testing

Test the integration:

```bash
# Start Mail2printer with API
python main.py --config config.yaml

# In Laravel, test the health endpoint
php artisan tinker
>>> app('App\Http\Controllers\Mail2PrinterController')->health()
```

## Troubleshooting

### "Connection refused"

- Ensure Mail2printer is running: `python main.py`
- Check API is enabled in `config.yaml`
- Verify URL in `.env` is correct

### "401 Unauthorized"

- Check API key matches in both systems
- Ensure API key is sent in header

### "Empty response"

- Check Mail2printer logs
- Verify printer is available
- Test API directly with curl

## Further Reading

- [Mail2printer API Documentation](../../docs/API.md)
- [Laravel HTTP Client](https://laravel.com/docs/http-client)
- [Laravel Configuration](https://laravel.com/docs/configuration)
