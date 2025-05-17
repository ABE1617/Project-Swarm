# Webhook Trigger Node for Project Swarm
import os
import uuid
import threading
import time
from flask import request

# Node Metadata
NODE_TYPE = "webhook_trigger"
NODE_NAME = "Webhook Trigger"
NODE_DESCRIPTION = "Waits for incoming HTTP requests at a webhook URL"
NODE_COLOR = "#61affe"
NODE_ICON = "fa-arrow-right"

# Configuration Schema
CONFIG_SCHEMA = {
    "path": {
        "type": "string",
        "title": "Webhook Path",
        "description": "Path suffix for the webhook URL (e.g., my-webhook)",
        "required": True
    },
    "method": {
        "type": "string",
        "title": "HTTP Method",
        "description": "Allowed HTTP method for the webhook",
        "enum": ["GET", "POST", "PUT", "DELETE", "ANY"],
        "default": "POST",
        "required": True
    },
    "secret": {
        "type": "string",
        "title": "Secret Token",
        "description": "Optional secret token for webhook authentication"
    },
    "timeout": {
        "type": "number",
        "title": "Timeout (seconds)",
        "description": "Maximum time to wait for a webhook request (in seconds)",
        "default": 120
    }
}

# Global registry to store active webhooks
_active_webhooks = {}

def run(config, context):
    """
    Creates a webhook endpoint and waits for a request
    
    Args:
        config (dict): Configuration for the webhook
        context (dict): Shared context from previous nodes
        
    Returns:
        dict: Webhook request data
    """
    webhook_path = config.get('path', '').strip('/')
    if not webhook_path:
        webhook_path = f"webhook-{uuid.uuid4().hex[:8]}"
    
    method = config.get('method', 'POST')
    secret = config.get('secret', '')
    timeout = int(config.get('timeout', 120))
    
    # Create full webhook URL
    base_url = os.environ.get('BASE_URL', 'http://localhost:5000')
    webhook_url = f"{base_url}/api/webhooks/{webhook_path}"
    
    # Create a unique ID for this webhook instance
    webhook_id = str(uuid.uuid4())
    
    # Create a shared data structure for the webhook handler and this function
    webhook_data = {
        'received': False,
        'payload': None,
        'headers': None,
        'method': None,
        'query_params': None,
        'error': None
    }
    
    # Register this webhook
    _active_webhooks[webhook_path] = {
        'id': webhook_id,
        'method': method,
        'secret': secret,
        'data': webhook_data
    }
    
    # Wait for webhook to be triggered or timeout
    start_time = time.time()
    
    while not webhook_data['received'] and (time.time() - start_time) < timeout:
        time.sleep(0.5)  # Check every half second
    
    # Unregister the webhook
    if webhook_path in _active_webhooks and _active_webhooks[webhook_path]['id'] == webhook_id:
        del _active_webhooks[webhook_path]
    
    # Check if we received data or timed out
    if webhook_data['received']:
        return {
            'payload': webhook_data['payload'],
            'headers': webhook_data['headers'],
            'method': webhook_data['method'],
            'query_params': webhook_data['query_params'],
            'webhook_url': webhook_url
        }
    else:
        return {
            'error': f"Webhook timed out after {timeout} seconds",
            'webhook_url': webhook_url
        }

# This function will be called by the Flask route handler
def handle_webhook(path, method, headers, args, json_data, form_data):
    """
    Process an incoming webhook request
    
    Called by the Flask route handler
    """
    if path not in _active_webhooks:
        return {'error': 'Webhook not found or expired'}, 404
    
    webhook = _active_webhooks[path]
    webhook_method = webhook['method']
    
    # Verify method if not ANY
    if webhook_method != 'ANY' and method != webhook_method:
        return {'error': f'Method not allowed. Expected {webhook_method}.'}, 405
    
    # Verify secret if specified
    if webhook['secret']:
        auth_header = headers.get('Authorization', '')
        if not auth_header.startswith('Bearer ') or auth_header[7:] != webhook['secret']:
            return {'error': 'Invalid or missing webhook secret'}, 401
    
    # Process payload based on content type
    if json_data is not None:
        payload = json_data
    elif form_data:
        payload = form_data
    else:
        payload = None
    
    # Update the webhook data
    webhook['data']['received'] = True
    webhook['data']['payload'] = payload
    webhook['data']['headers'] = dict(headers)
    webhook['data']['method'] = method
    webhook['data']['query_params'] = dict(args)
    
    return {'success': True, 'message': 'Webhook received'}, 200