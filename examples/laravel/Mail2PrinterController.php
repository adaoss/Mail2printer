<?php

/**
 * Example Laravel Controller for Mail2printer Integration
 * 
 * This example shows how to integrate Mail2printer REST API
 * into your Laravel application.
 * 
 * Installation:
 * 1. Place this file in app/Http/Controllers/
 * 2. Create the service in app/Services/Mail2PrinterService.php
 * 3. Add routes to routes/web.php
 * 4. Configure in .env
 */

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

class Mail2PrinterController extends Controller
{
    protected $baseUrl;
    protected $apiKey;

    public function __construct()
    {
        $this->baseUrl = config('services.mail2printer.url', 'http://localhost:5000');
        $this->apiKey = config('services.mail2printer.api_key');
    }

    /**
     * Make an authenticated API request
     */
    protected function apiRequest($method, $endpoint, $data = [])
    {
        $url = $this->baseUrl . $endpoint;
        
        $request = Http::timeout(10)->withHeaders([
            'X-API-Key' => $this->apiKey,
            'Accept' => 'application/json',
        ]);

        try {
            switch (strtoupper($method)) {
                case 'GET':
                    $response = $request->get($url);
                    break;
                case 'POST':
                    $response = $request->post($url, $data);
                    break;
                case 'DELETE':
                    $response = $request->delete($url);
                    break;
                default:
                    throw new \Exception("Unsupported HTTP method: $method");
            }

            if ($response->successful()) {
                return $response->json();
            }

            Log::error('Mail2printer API error', [
                'status' => $response->status(),
                'body' => $response->body()
            ]);

            return null;

        } catch (\Exception $e) {
            Log::error('Mail2printer connection error', [
                'message' => $e->getMessage()
            ]);
            return null;
        }
    }

    /**
     * Display printer dashboard
     */
    public function dashboard()
    {
        $status = $this->apiRequest('GET', '/api/status');
        $printerStatus = $this->apiRequest('GET', '/api/printer/status');
        $stats = $this->apiRequest('GET', '/api/stats');

        return view('mail2printer.dashboard', [
            'status' => $status,
            'printerStatus' => $printerStatus,
            'stats' => $stats,
        ]);
    }

    /**
     * List all print jobs
     */
    public function jobs()
    {
        $result = $this->apiRequest('GET', '/api/printer/jobs');
        
        if (!$result || !$result['success']) {
            return back()->with('error', 'Failed to fetch print jobs');
        }

        return view('mail2printer.jobs', [
            'jobs' => $result['data']['jobs'] ?? [],
            'count' => $result['data']['count'] ?? 0,
        ]);
    }

    /**
     * Get job status
     */
    public function jobStatus($id)
    {
        $result = $this->apiRequest('GET', "/api/printer/jobs/{$id}");
        
        if (!$result || !$result['success']) {
            return response()->json([
                'error' => 'Failed to get job status'
            ], 500);
        }

        return response()->json($result['data']);
    }

    /**
     * Cancel a print job
     */
    public function cancelJob($id)
    {
        $result = $this->apiRequest('POST', "/api/printer/jobs/{$id}/cancel");
        
        if (!$result || !$result['success']) {
            return back()->with('error', 'Failed to cancel job');
        }

        return back()->with('success', "Job {$id} cancelled successfully");
    }

    /**
     * Get printer statistics
     */
    public function statistics()
    {
        $stats = $this->apiRequest('GET', '/api/stats');
        $printerStatus = $this->apiRequest('GET', '/api/printer/status');

        return view('mail2printer.statistics', [
            'stats' => $stats['data'] ?? [],
            'printer' => $printerStatus['data'] ?? [],
        ]);
    }

    /**
     * Restart Mail2printer service
     */
    public function restart()
    {
        $result = $this->apiRequest('POST', '/api/service/restart');
        
        if (!$result || !$result['success']) {
            return back()->with('error', 'Failed to restart service');
        }

        return back()->with('success', 'Service restart requested');
    }

    /**
     * API health check
     */
    public function health()
    {
        $result = $this->apiRequest('GET', '/health');
        
        if (!$result) {
            return response()->json([
                'status' => 'error',
                'message' => 'Service not available'
            ], 503);
        }

        return response()->json($result);
    }
}
