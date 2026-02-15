"""
REST API for Mail2printer service

Provides endpoints for Laravel app to:
- Get printer status
- Get service statistics
- Restart service
- Cancel print jobs
- List print jobs
"""

import logging
import os
import signal
from typing import Optional
from functools import wraps
from flask import Flask, jsonify, request, Response
from .printer_manager import PrinterManager
from .service import Mail2PrinterService

logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global service instance (will be set by main.py)
_service: Optional[Mail2PrinterService] = None
_api_key: Optional[str] = None


def set_service(service: Mail2PrinterService):
    """Set the service instance for API access"""
    global _service
    _service = service


def set_api_key(key: str):
    """Set the API key for authentication"""
    global _api_key
    _api_key = key


def require_api_key(f):
    """Decorator to require API key authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not _api_key:
            # API key not configured, allow all requests
            return f(*args, **kwargs)
        
        # Check for API key in header or query parameter
        provided_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        
        if not provided_key or provided_key != _api_key:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Valid API key required'
            }), 401
        
        return f(*args, **kwargs)
    return decorated_function


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'service': 'mail2printer',
        'version': '1.0.0'
    })


@app.route('/api/status', methods=['GET'])
@require_api_key
def get_status():
    """Get service status"""
    if not _service:
        return jsonify({
            'error': 'Service not initialized'
        }), 503
    
    try:
        status = _service.get_status()
        return jsonify({
            'success': True,
            'data': status
        })
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/stats', methods=['GET'])
@require_api_key
def get_stats():
    """Get service statistics"""
    if not _service:
        return jsonify({
            'error': 'Service not initialized'
        }), 503
    
    try:
        stats = _service.stats.copy()
        
        # Add uptime calculation
        import time
        if stats.get('service_start_time'):
            uptime_seconds = time.time() - stats['service_start_time']
            stats['uptime_seconds'] = int(uptime_seconds)
            stats['uptime_formatted'] = _format_uptime(uptime_seconds)
        
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/printer/status', methods=['GET'])
@require_api_key
def get_printer_status():
    """Get printer status and statistics"""
    if not _service:
        return jsonify({
            'error': 'Service not initialized'
        }), 503
    
    try:
        printer_stats = _service.printer_manager.get_printer_stats()
        
        # Add printer connection test
        printer_available = _service.printer_manager.test_connection()
        printer_stats['online'] = printer_available
        
        return jsonify({
            'success': True,
            'data': printer_stats
        })
    except Exception as e:
        logger.error(f"Error getting printer status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/printer/jobs', methods=['GET'])
@require_api_key
def list_print_jobs():
    """List all print jobs"""
    if not _service:
        return jsonify({
            'error': 'Service not initialized'
        }), 503
    
    try:
        jobs = _service.printer_manager.get_all_jobs()
        
        # Convert job data to JSON-serializable format
        jobs_list = []
        for job_id, job_info in jobs.items():
            jobs_list.append({
                'job_id': job_id,
                'info': job_info
            })
        
        return jsonify({
            'success': True,
            'data': {
                'jobs': jobs_list,
                'count': len(jobs_list)
            }
        })
    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/printer/jobs/<int:job_id>', methods=['GET'])
@require_api_key
def get_job_status(job_id: int):
    """Get status of a specific print job"""
    if not _service:
        return jsonify({
            'error': 'Service not initialized'
        }), 503
    
    try:
        status = _service.printer_manager.get_print_status(job_id)
        
        return jsonify({
            'success': True,
            'data': {
                'job_id': job_id,
                'status': status
            }
        })
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/printer/jobs/<int:job_id>/cancel', methods=['POST', 'DELETE'])
@require_api_key
def cancel_print_job(job_id: int):
    """Cancel a print job"""
    if not _service:
        return jsonify({
            'error': 'Service not initialized'
        }), 503
    
    try:
        success = _service.printer_manager.cancel_job(job_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Job {job_id} cancelled successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Failed to cancel job {job_id}'
            }), 400
    except Exception as e:
        logger.error(f"Error cancelling job: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/service/restart', methods=['POST'])
@require_api_key
def restart_service():
    """Restart the service (requires supervisor or systemd)"""
    try:
        # Send SIGHUP signal to self (graceful reload)
        # This works if the service is managed by supervisor or systemd
        pid = os.getpid()
        os.kill(pid, signal.SIGHUP)
        
        return jsonify({
            'success': True,
            'message': 'Service restart requested',
            'pid': pid
        })
    except Exception as e:
        logger.error(f"Error restarting service: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/service/stop', methods=['POST'])
@require_api_key
def stop_service():
    """Stop the service"""
    if not _service:
        return jsonify({
            'error': 'Service not initialized'
        }), 503
    
    try:
        # Stop the service gracefully
        _service.stop()
        
        return jsonify({
            'success': True,
            'message': 'Service stopped'
        })
    except Exception as e:
        logger.error(f"Error stopping service: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'error': 'Not found',
        'message': 'The requested endpoint does not exist'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred'
    }), 500


def _format_uptime(seconds: float) -> str:
    """Format uptime in human-readable form"""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def run_api_server(host: str = '0.0.0.0', port: int = 5000, debug: bool = False):
    """Run the API server"""
    logger.info(f"Starting API server on {host}:{port}")
    app.run(host=host, port=port, debug=debug, threaded=True)


if __name__ == '__main__':
    # For testing purposes
    run_api_server(debug=True)
