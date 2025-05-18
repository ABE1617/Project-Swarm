# HTTP Request Node for Project Swarm
import requests
import logging
import json
import time
from datetime import datetime

# Configure node logger
logger = logging.getLogger(__name__)

# Node Metadata
NODE_TYPE = "http_request"
NODE_NAME = "HTTP Request"
NODE_DESCRIPTION = "Make HTTP requests to APIs and web services"
NODE_COLOR = "#61affe"
NODE_ICON = "fa-globe"

# Configuration Schema
CONFIG_SCHEMA = {
    "url": {
        "type": "string",
        "title": "URL",
        "description": "URL to make the request to",
        "required": True
    },
    "method": {
        "type": "string",
        "title": "Method",
        "description": "HTTP Method",
        "enum": ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
        "default": "GET",
        "required": True
    },
    "headers": {
        "type": "object",
        "title": "Headers",
        "description": "HTTP Headers to include with the request"
    },
    "params": {
        "type": "object",
        "title": "Query Parameters",
        "description": "URL query parameters"
    },
    "body": {
        "type": "string",
        "title": "Request Body",
        "description": "Body to send with the request (for POST, PUT, etc.)"
    },
    "json": {
        "type": "object",
        "title": "JSON Body",
        "description": "JSON data to send (alternative to body)"
    },
    "auth": {
        "type": "object",
        "title": "Authentication",
        "description": "Authentication credentials",
        "properties": {
            "username": {
                "type": "string",
                "title": "Username"
            },
            "password": {
                "type": "string",
                "title": "Password"
            }
        }
    }
}

def run(config, context):
    """
    Makes an HTTP request based on the provided configuration
    
    Args:
        config (dict): Configuration for the request
        context (dict): Shared context from previous nodes
        
    Returns:
        dict: Response data and metadata
    """
    start_time = time.time()
    logger.info(f"Starting HTTP request execution at {datetime.now().isoformat()}")
    
    # Log configuration (with sensitive data masked)
    masked_config = mask_sensitive_config(config)
    logger.debug(f"Request configuration: {json.dumps(masked_config, indent=2)}")
    
    url = config.get('url')
    if not url:
        logger.error("URL is required but not provided")
        raise ValueError("URL is required")
    
    method = config.get('method', 'GET')
    headers = config.get('headers', {})
    params = config.get('params', {})
    body = config.get('body')
    json_data = config.get('json')
    auth = config.get('auth')
    
    # Log request details
    logger.info(f"Preparing {method} request to {url}")
    if params:
        logger.debug(f"Query parameters: {json.dumps(params, indent=2)}")
    if headers:
        masked_headers = mask_sensitive_headers(headers)
        logger.debug(f"Headers: {json.dumps(masked_headers, indent=2)}")
    if body:
        logger.debug(f"Request has body of length: {len(str(body))}")
    if json_data:
        logger.debug(f"Request has JSON payload: {json.dumps(mask_sensitive_data(json_data), indent=2)}")
    
    # Authentication tuple
    auth_tuple = None
    if auth and 'username' in auth and 'password' in auth:
        auth_tuple = (auth['username'], auth['password'])
        logger.info(f"Using basic authentication with username: {auth['username']}")
    
    try:
        # Make the request
        logger.info(f"Sending {method} request to {url}")
        request_start = time.time()
        
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            data=body,
            json=json_data,
            auth=auth_tuple,
            timeout=30
        )
        
        request_time = time.time() - request_start
        logger.info(f"Received response in {request_time:.3f} seconds with status code {response.status_code}")
        
        # Log response headers
        logger.debug(f"Response headers: {json.dumps(dict(response.headers), indent=2)}")
        
        # Try to parse response as JSON, fall back to text
        try:
            response_data = response.json()
            logger.debug("Successfully parsed response as JSON")
            if isinstance(response_data, dict):
                logger.debug(f"Response data keys: {list(response_data.keys())}")
        except ValueError:
            response_data = response.text
            logger.debug(f"Response is text of length: {len(response_data)}")
        
        # Prepare result
        result = {
            'status_code': response.status_code,
            'headers': dict(response.headers),
            'response': response_data,
            'url': response.url,
            'time': response.elapsed.total_seconds(),
            'total_time': time.time() - start_time
        }
        
        logger.info(f"HTTP request completed successfully in {result['total_time']:.3f} seconds")
        return result
        
    except requests.exceptions.Timeout:
        error_msg = f"Request to {url} timed out after 30 seconds"
        logger.error(error_msg)
        raise TimeoutError(error_msg)
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Request failed: {str(e)}"
        logger.error(error_msg)
        raise

def mask_sensitive_config(config):
    """Mask sensitive data in configuration for logging"""
    masked = config.copy()
    if 'auth' in masked:
        if isinstance(masked['auth'], dict):
            if 'password' in masked['auth']:
                masked['auth']['password'] = '***'
    if 'headers' in masked:
        masked['headers'] = mask_sensitive_headers(masked['headers'])
    return masked

def mask_sensitive_headers(headers):
    """Mask sensitive data in headers"""
    masked = headers.copy()
    sensitive_headers = ['authorization', 'x-api-key', 'api-key', 'token']
    for header in masked:
        if header.lower() in sensitive_headers:
            masked[header] = '***'
    return masked

def mask_sensitive_data(data):
    """Mask sensitive data in JSON payload"""
    if isinstance(data, dict):
        masked = {}
        sensitive_keys = ['password', 'token', 'api_key', 'secret', 'key']
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                masked[key] = '***'
            else:
                masked[key] = mask_sensitive_data(value)
        return masked
    elif isinstance(data, list):
        return [mask_sensitive_data(item) for item in data]
    else:
        return data
