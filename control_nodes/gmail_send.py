# Gmail Send Node for Project Swarm
import os
import json
import base64
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Node Metadata
NODE_TYPE = "gmail_send"
NODE_NAME = "Send Email (Gmail)"
NODE_DESCRIPTION = "Send emails using the Gmail API"
NODE_COLOR = "#f44336"
NODE_ICON = "fab fa-google"

# Configuration Schema
CONFIG_SCHEMA = {
    "google_credentials": {
        "type": "string",
        "title": "Google API Credentials",
        "description": "OAuth credentials JSON or path to credentials file",
        "required": True
    },
    "to": {
        "type": "string",
        "title": "To",
        "description": "Recipient email address(es), comma-separated",
        "required": True
    },
    "subject": {
        "type": "string",
        "title": "Subject",
        "description": "Email subject line",
        "required": True
    },
    "body": {
        "type": "string",
        "title": "Body",
        "description": "Email body content",
        "required": True
    },
    "cc": {
        "type": "string",
        "title": "CC",
        "description": "CC recipients, comma-separated"
    },
    "bcc": {
        "type": "string",
        "title": "BCC",
        "description": "BCC recipients, comma-separated"
    },
    "html": {
        "type": "boolean",
        "title": "HTML Email",
        "description": "Send as HTML email",
        "default": True
    }
}

def run(config, context):
    """
    Sends an email using the Gmail API
    
    Args:
        config (dict): Configuration for the email
        context (dict): Shared context from previous nodes
        
    Returns:
        dict: Result of the operation
    """
    credentials_data = config.get('google_credentials', os.environ.get('GOOGLE_GMAIL_CREDENTIALS'))
    to_email = config.get('to', '')
    subject = config.get('subject', '')
    body = config.get('body', '')
    cc = config.get('cc', '')
    bcc = config.get('bcc', '')
    html = config.get('html', True)
    
    if not credentials_data:
        raise ValueError("Google API credentials are required. Either provide them in the configuration or set the GOOGLE_GMAIL_CREDENTIALS environment variable.")
    
    if not to_email:
        raise ValueError("Recipient email address is required")
    
    if not subject:
        raise ValueError("Email subject is required")
    
    if not body:
        raise ValueError("Email body is required")
    
    try:
        # Get an access token for Gmail API
        access_token = get_gmail_access_token(credentials_data)
        
        # Create the email message
        message = create_email_message(to_email, subject, body, cc, bcc, html)
        
        # Encode the message for Gmail API
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        # Send the email
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'raw': encoded_message
        }
        
        response = requests.post(
            'https://gmail.googleapis.com/gmail/v1/users/me/messages/send',
            headers=headers,
            json=data
        )
        
        if response.status_code in (200, 201):
            result = response.json()
            return {
                'success': True,
                'message_id': result.get('id', ''),
                'thread_id': result.get('threadId', ''),
                'to': to_email,
                'subject': subject
            }
        else:
            error_data = response.json() if response.content else {"error": f"HTTP error {response.status_code}"}
            raise ValueError(f"Gmail API error: {error_data}")
    
    except Exception as e:
        raise ValueError(f"Error sending email with Gmail API: {str(e)}")

def create_email_message(to, subject, body, cc='', bcc='', html=True):
    """Creates an email message object"""
    message = MIMEMultipart()
    message['To'] = to
    message['Subject'] = subject
    
    if cc:
        message['Cc'] = cc
    
    if bcc:
        message['Bcc'] = bcc
    
    # Attach body content
    if html:
        message.attach(MIMEText(body, 'html'))
    else:
        message.attach(MIMEText(body, 'plain'))
    
    return message

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