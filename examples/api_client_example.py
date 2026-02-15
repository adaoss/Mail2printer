#!/usr/bin/env python3
"""
Example API client for Mail2printer
Demonstrates how to interact with the REST API
"""

import requests
import json
import sys

# Configuration
BASE_URL = "http://localhost:5000"
API_KEY = "your-api-key-here"  # Set to None if no API key is configured

def make_request(method, endpoint, data=None):
    """Make an API request"""
    url = f"{BASE_URL}{endpoint}"
    headers = {}
    
    if API_KEY:
        headers['X-API-Key'] = API_KEY
    
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=data)
        elif method == 'DELETE':
            response = requests.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        return response.json()
    except requests.exceptions.ConnectionError:
        print(f"❌ Error: Could not connect to {BASE_URL}")
        print("   Make sure Mail2printer service is running with API enabled")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

def print_response(title, response):
    """Pretty print API response"""
    print(f"\n{'='*60}")
    print(f"📋 {title}")
    print('='*60)
    print(json.dumps(response, indent=2))

def main():
    """Run API examples"""
    print("Mail2printer REST API Client")
    print(f"Connecting to: {BASE_URL}")
    
    # 1. Health Check
    response = make_request('GET', '/health')
    print_response("Health Check", response)
    
    # 2. Get Service Status
    response = make_request('GET', '/api/status')
    print_response("Service Status", response)
    
    # 3. Get Statistics
    response = make_request('GET', '/api/stats')
    print_response("Service Statistics", response)
    
    # 4. Get Printer Status
    response = make_request('GET', '/api/printer/status')
    print_response("Printer Status", response)
    
    # 5. List Print Jobs
    response = make_request('GET', '/api/printer/jobs')
    print_response("Print Jobs", response)
    
    # If there are jobs, demonstrate getting job status
    if response.get('success') and response.get('data', {}).get('jobs'):
        jobs = response['data']['jobs']
        if jobs:
            job_id = jobs[0]['job_id']
            response = make_request('GET', f'/api/printer/jobs/{job_id}')
            print_response(f"Job {job_id} Status", response)
    
    print("\n" + "="*60)
    print("✅ All API calls successful!")
    print("="*60)

if __name__ == '__main__':
    # Check if requests is installed
    try:
        import requests
    except ImportError:
        print("❌ Error: 'requests' library not found")
        print("   Install it with: pip install requests")
        sys.exit(1)
    
    main()
