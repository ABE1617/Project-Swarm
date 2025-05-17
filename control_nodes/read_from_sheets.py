# Read from Google Sheets Node for Project Swarm
import os
import json
import base64
import requests

# Node Metadata
NODE_TYPE = "read_from_sheets"
NODE_NAME = "Read from Google Sheets"
NODE_DESCRIPTION = "Read data from a Google Sheets spreadsheet"
NODE_COLOR = "#2196f3"
NODE_ICON = "fa-table"

# Configuration Schema
CONFIG_SCHEMA = {
    "google_credentials": {
        "type": "string",
        "title": "Google API Credentials",
        "description": "Service account credentials JSON or path to credentials file",
        "required": True
    },
    "spreadsheet_id": {
        "type": "string",
        "title": "Spreadsheet ID",
        "description": "ID of the Google Sheet (from URL)",
        "required": True
    },
    "range": {
        "type": "string",
        "title": "Range",
        "description": "Range to read (e.g., 'Sheet1!A1:D10' or just 'Sheet1')",
        "required": True
    },
    "include_headers": {
        "type": "boolean",
        "title": "Include Headers",
        "description": "Treat first row as headers",
        "default": True
    },
    "output_format": {
        "type": "string",
        "title": "Output Format",
        "description": "Format of the returned data",
        "enum": ["array", "object"],
        "default": "object"
    }
}

def run(config, context):
    """
    Reads data from a Google Sheet
    
    Args:
        config (dict): Configuration for the operation
        context (dict): Shared context from previous nodes
        
    Returns:
        dict: Data from the spreadsheet
    """
    credentials_data = config.get('google_credentials', os.environ.get('GOOGLE_CREDENTIALS'))
    spreadsheet_id = config.get('spreadsheet_id')
    range_name = config.get('range')
    include_headers = config.get('include_headers', True)
    output_format = config.get('output_format', 'object')
    
    if not credentials_data:
        raise ValueError("Google API credentials are required. Either provide them in the configuration or set the GOOGLE_CREDENTIALS environment variable.")
    
    if not spreadsheet_id:
        raise ValueError("Spreadsheet ID is required")
    
    if not range_name:
        raise ValueError("Range is required")
    
    # Authenticate with Google Sheets API
    try:
        # Check if credentials_data is a path to a file
        if os.path.isfile(credentials_data):
            with open(credentials_data, 'r') as f:
                credentials_json = f.read()
        else:
            # Assume it's the JSON content directly
            credentials_json = credentials_data
        
        # Get an access token
        access_token = get_access_token(credentials_json)
        
        # Make the API request
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        
        url = f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range_name}'
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            values = result.get('values', [])
            
            # Process the data based on the output format
            if output_format == 'object' and include_headers and len(values) > 1:
                # Use first row as headers and convert to list of objects
                headers = values[0]
                data = []
                
                for row in values[1:]:
                    row_obj = {}
                    for i, value in enumerate(row):
                        if i < len(headers):
                            row_obj[headers[i]] = value
                    data.append(row_obj)
            else:
                # Return as array
                data = values
            
            return {
                'data': data,
                'spreadsheet_id': spreadsheet_id,
                'range': result.get('range', range_name),
                'num_rows': len(values),
                'num_columns': max(len(row) for row in values) if values else 0
            }
        else:
            error_data = response.json() if response.content else {"error": f"HTTP error {response.status_code}"}
            raise ValueError(f"Google Sheets API error: {error_data}")
    
    except Exception as e:
        raise ValueError(f"Error reading from Google Sheet: {str(e)}")

def get_access_token(credentials_json):
    """Get an access token from Google using service account credentials"""
    try:
        # Parse the credentials JSON
        creds = json.loads(credentials_json)
        
        # Create a JWT
        header = {
            "alg": "RS256",
            "typ": "JWT"
        }
        
        # Encode header
        header_encoded = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
        
        # Current time
        import time
        current_time = int(time.time())
        
        # Create claims
        claims = {
            "iss": creds['client_email'],
            "scope": "https://www.googleapis.com/auth/spreadsheets.readonly",
            "aud": creds['token_uri'],
            "exp": current_time + 3600,  # 1 hour
            "iat": current_time
        }
        
        # Encode claims
        claims_encoded = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip('=')
        
        # Create the JWT payload
        jwt_payload = f"{header_encoded}.{claims_encoded}"
        
        # Sign the JWT
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.primitives.serialization import load_pem_private_key
        
        # Load the private key
        private_key = load_pem_private_key(
            creds['private_key'].encode(),
            password=None
        )
        
        # Sign the JWT payload
        signature = private_key.sign(
            jwt_payload.encode(),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        
        # Encode the signature
        signature_encoded = base64.urlsafe_b64encode(signature).decode().rstrip('=')
        
        # Create the JWT
        jwt = f"{jwt_payload}.{signature_encoded}"
        
        # Exchange the JWT for an access token
        token_data = {
            'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
            'assertion': jwt
        }
        
        response = requests.post(creds['token_uri'], data=token_data)
        
        if response.status_code == 200:
            return response.json()['access_token']
        else:
            raise ValueError(f"Failed to get access token: {response.text}")
    
    except Exception as e:
        raise ValueError(f"Error getting access token: {str(e)}")

# Note: This implementation requires the 'cryptography' package for JWT signing
# In a production environment, consider using the Google API client library instead