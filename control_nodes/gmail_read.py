# Gmail Read Node for Project Swarm
import os
import json
import base64
import requests
import email
from email.header import decode_header

# Node Metadata
NODE_TYPE = "gmail_read"
NODE_NAME = "Read Email (Gmail)"
NODE_DESCRIPTION = "Read emails from Gmail inbox"
NODE_COLOR = "#f44336"
NODE_ICON = "fas fa-envelope-open"

# Configuration Schema
CONFIG_SCHEMA = {
    "google_credentials": {
        "type": "string",
        "title": "Google API Credentials",
        "description": "OAuth credentials JSON or path to credentials file",
        "required": True
    },
    "query": {
        "type": "string",
        "title": "Search Query",
        "description": "Gmail search query (e.g., 'is:unread', 'from:example@example.com')",
        "default": "is:unread"
    },
    "max_results": {
        "type": "number",
        "title": "Maximum Results",
        "description": "Maximum number of emails to retrieve",
        "default": 10
    },
    "mark_as_read": {
        "type": "boolean",
        "title": "Mark as Read",
        "description": "Mark retrieved emails as read",
        "default": False
    },
    "include_attachments": {
        "type": "boolean",
        "title": "Include Attachments",
        "description": "Retrieve email attachments",
        "default": False
    }
}

def run(config, context):
    """
    Reads emails from Gmail
    
    Args:
        config (dict): Configuration for the operation
        context (dict): Shared context from previous nodes
        
    Returns:
        dict: Retrieved emails
    """
    credentials_data = config.get('google_credentials', os.environ.get('GOOGLE_GMAIL_CREDENTIALS'))
    query = config.get('query', 'is:unread')
    max_results = int(config.get('max_results', 10))
    mark_as_read = config.get('mark_as_read', False)
    include_attachments = config.get('include_attachments', False)
    
    if not credentials_data:
        raise ValueError("Google API credentials are required. Either provide them in the configuration or set the GOOGLE_GMAIL_CREDENTIALS environment variable.")
    
    try:
        # Get an access token for Gmail API
        access_token = get_gmail_access_token(credentials_data)
        
        # Set up headers for API requests
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Search for messages matching the query
        search_url = f'https://gmail.googleapis.com/gmail/v1/users/me/messages?q={query}&maxResults={max_results}'
        search_response = requests.get(search_url, headers=headers)
        
        if search_response.status_code != 200:
            error_data = search_response.json() if search_response.content else {"error": f"HTTP error {search_response.status_code}"}
            raise ValueError(f"Gmail API error in search: {error_data}")
        
        search_results = search_response.json()
        messages = search_results.get('messages', [])
        
        # If no messages found, return empty result
        if not messages:
            return {
                'emails': [],
                'count': 0,
                'query': query
            }
        
        # Retrieve full message details
        emails = []
        
        for message_data in messages:
            message_id = message_data['id']
            
            # Get full message
            message_url = f'https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}'
            message_response = requests.get(message_url, headers=headers)
            
            if message_response.status_code != 200:
                continue  # Skip this message on error
            
            message = message_response.json()
            
            # Extract headers
            headers_data = {}
            for header in message.get('payload', {}).get('headers', []):
                name = header.get('name', '').lower()
                value = header.get('value', '')
                headers_data[name] = value
            
            # Get message body
            body = extract_body(message.get('payload', {}), include_attachments)
            
            # Create email object
            email_obj = {
                'id': message_id,
                'thread_id': message.get('threadId', ''),
                'labels': message.get('labelIds', []),
                'snippet': message.get('snippet', ''),
                'subject': headers_data.get('subject', ''),
                'from': headers_data.get('from', ''),
                'to': headers_data.get('to', ''),
                'date': headers_data.get('date', ''),
                'body': body.get('text', ''),
                'body_html': body.get('html', ''),
                'attachments': body.get('attachments', [])
            }
            
            emails.append(email_obj)
            
            # Mark as read if requested
            if mark_as_read and 'UNREAD' in message.get('labelIds', []):
                modify_url = f'https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}/modify'
                modify_data = {
                    'removeLabelIds': ['UNREAD']
                }
                requests.post(modify_url, headers=headers, json=modify_data)
        
        return {
            'emails': emails,
            'count': len(emails),
            'query': query
        }
    
    except Exception as e:
        raise ValueError(f"Error reading emails from Gmail: {str(e)}")

def extract_body(payload, include_attachments=False):
    """Extract the body content and attachments from a message payload"""
    result = {
        'text': '',
        'html': '',
        'attachments': []
    }
    
    if not payload:
        return result
    
    # Handle multipart messages
    if 'parts' in payload:
        for part in payload['parts']:
            part_result = extract_body(part, include_attachments)
            
            # Combine text and HTML parts
            if part_result['text']:
                result['text'] += part_result['text']
            
            if part_result['html']:
                result['html'] += part_result['html']
            
            # Add attachments
            result['attachments'].extend(part_result['attachments'])
    
    # Handle non-multipart message or specific part
    elif 'body' in payload:
        mime_type = payload.get('mimeType', '')
        body_data = payload['body'].get('data', '')
        
        if body_data:
            decoded_data = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='replace')
            
            if 'text/plain' in mime_type:
                result['text'] = decoded_data
            elif 'text/html' in mime_type:
                result['html'] = decoded_data
        
        # Handle attachments
        filename = None
        for header in payload.get('headers', []):
            if header.get('name', '').lower() == 'content-disposition':
                # Extract filename from content-disposition
                parts = header.get('value', '').split(';')
                for part in parts:
                    part = part.strip()
                    if part.startswith('filename='):
                        filename = part[9:].strip('"\'')
                        break
        
        if include_attachments and 'attachmentId' in payload['body'] and filename:
            # This is an attachment
            result['attachments'].append({
                'id': payload['body']['attachmentId'],
                'filename': filename,
                'mime_type': mime_type,
                'size': payload['body'].get('size', 0)
            })
    
    return result

def get_gmail_access_token(credentials_data):
    """Get an access token for Gmail API"""
    try:
        # Check if credentials_data is a path to a file
        if os.path.isfile(credentials_data):
            with open(credentials_data, 'r') as f:
                credentials_json = f.read()
        else:
            # Assume it's the JSON content directly
            credentials_json = credentials_data
        
        # Parse the credentials JSON
        creds = json.loads(credentials_json)
        
        # This is a simplified implementation
        # In a real application, you should implement the full OAuth 2.0 flow
        # including refreshing tokens and getting user consent
        
        # For this example, we'll assume the credentials already contain a valid access token
        if 'access_token' in creds:
            return creds['access_token']
        else:
            raise ValueError("The provided credentials do not contain an access token. Please provide OAuth2 credentials with a valid access token.")
    
    except Exception as e:
        raise ValueError(f"Error getting Gmail access token: {str(e)}")

# Note: In a production environment, implement the full OAuth2 flow
# This implementation assumes pre-authorized credentials with a valid access token