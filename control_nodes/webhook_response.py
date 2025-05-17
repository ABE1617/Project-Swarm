# Webhook Response Node for Project Swarm
import json

# Node Metadata
NODE_TYPE = "webhook_response"
NODE_NAME = "Webhook Response"
NODE_DESCRIPTION = "Send a response back to a webhook request"
NODE_COLOR = "#61affe"
NODE_ICON = "fa-reply"

# Configuration Schema
CONFIG_SCHEMA = {
    "status_code": {
        "type": "number",
        "title": "Status Code",
        "description": "HTTP status code for the response",
        "default": 200,
        "required": True
    },
    "content_type": {
        "type": "string",
        "title": "Content Type",
        "description": "Response content type",
        "enum": ["application/json", "text/plain", "text/html", "application/xml"],
        "default": "application/json",
        "required": True
    },
    "body": {
        "type": "string",
        "title": "Response Body",
        "description": "Content to send in the response",
        "required": True
    },
    "headers": {
        "type": "object",
        "title": "Response Headers",
        "description": "Optional HTTP headers to include in the response"
    }
}

def run(config, context):
    """
    Configures a response for a webhook request
    
    Args:
        config (dict): Configuration for the response
        context (dict): Shared context from previous nodes
        
    Returns:
        dict: Response configuration
    """
    status_code = int(config.get('status_code', 200))
    content_type = config.get('content_type', 'application/json')
    body = config.get('body', '')
    headers = config.get('headers', {})
    
    # Format body based on content type
    if content_type == 'application/json' and isinstance(body, str):
        try:
            # See if it's valid JSON
            json.loads(body)
        except:
            # It's not valid JSON, so try to convert it
            try:
                body = json.dumps({'message': body})
            except:
                # If conversion fails, keep as plain string
                pass
    
    # Combine all data into a response object
    response = {
        'status_code': status_code,
        'content_type': content_type,
        'body': body,
        'headers': headers
    }
    
    return response