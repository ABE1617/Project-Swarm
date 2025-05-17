# Email Send Node for Project Swarm
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

# Node Metadata
NODE_TYPE = "email_send"
NODE_NAME = "Send Email"
NODE_DESCRIPTION = "Send emails using SMTP"
NODE_COLOR = "#9c27b0"
NODE_ICON = "fa-envelope"

# Configuration Schema
CONFIG_SCHEMA = {
    "to": {
        "type": "string",
        "title": "To",
        "description": "Recipient email address",
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
    "html": {
        "type": "boolean",
        "title": "HTML Email",
        "description": "Send as HTML email",
        "default": False
    },
    "from_email": {
        "type": "string",
        "title": "From Email",
        "description": "Sender email address (defaults to env var)"
    },
    "smtp_server": {
        "type": "string",
        "title": "SMTP Server",
        "description": "SMTP server hostname (defaults to env var)"
    },
    "smtp_port": {
        "type": "number",
        "title": "SMTP Port",
        "description": "SMTP server port (defaults to env var or 587)"
    },
    "username": {
        "type": "string",
        "title": "SMTP Username",
        "description": "SMTP authentication username (defaults to env var)"
    },
    "password": {
        "type": "string",
        "title": "SMTP Password",
        "description": "SMTP authentication password (defaults to env var)"
    }
}

def run(config, context):
    """
    Sends an email using SMTP
    
    Args:
        config (dict): Configuration for the email
        context (dict): Shared context from previous nodes
        
    Returns:
        dict: Result of the operation
    """
    # Required parameters
    to_email = config.get('to')
    subject = config.get('subject')
    body = config.get('body')
    
    if not to_email or not subject or not body:
        raise ValueError("To email, subject, and body are required")
    
    # Optional parameters with environment fallbacks
    from_email = config.get('from_email', os.getenv('SMTP_FROM_EMAIL'))
    smtp_server = config.get('smtp_server', os.getenv('SMTP_SERVER'))
    smtp_port = int(config.get('smtp_port', os.getenv('SMTP_PORT', 587)))
    username = config.get('username', os.getenv('SMTP_USERNAME'))
    password = config.get('password', os.getenv('SMTP_PASSWORD'))
    html = config.get('html', False)
    
    if not from_email or not smtp_server or not username or not password:
        return {
            'success': False,
            'error': 'Missing SMTP configuration. Provide in node config or environment variables.',
            'simulation': 'Email would be sent in production with proper configuration.'
        }
    
    # Create message
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    
    # Attach body
    if html:
        msg.attach(MIMEText(body, 'html'))
    else:
        msg.attach(MIMEText(body, 'plain'))
    
    # Send email
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(username, password)
        text = msg.as_string()
        server.sendmail(from_email, to_email, text)
        server.quit()
        
        return {
            'success': True,
            'to': to_email,
            'subject': subject,
            'html': html
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
