# HTTP Request Node for Project Swarm
import requests

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
    url = config.get('url')
    if not url:
        raise ValueError("URL is required")
    
    method = config.get('method', 'GET')
    headers = config.get('headers', {})
    params = config.get('params', {})
    body = config.get('body')
    json_data = config.get('json')
    auth = config.get('auth')
    
    # Authentication tuple
    auth_tuple = None
    if auth and 'username' in auth and 'password' in auth:
        auth_tuple = (auth['username'], auth['password'])
    
    # Make the request
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
    
    # Try to parse response as JSON, fall back to text
    try:
        response_data = response.json()
    except ValueError:
        response_data = response.text
    
    # Return response data and metadata
    return {
        'status_code': response.status_code,
        'headers': dict(response.headers),
        'response': response_data,
        'url': response.url,
        'time': response.elapsed.total_seconds()
    }
