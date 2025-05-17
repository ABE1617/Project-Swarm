# Save to Google Sheets Node for Project Swarm
import os
import json
import base64
import requests

# Node Metadata
NODE_TYPE = "save_to_sheets"
NODE_NAME = "Save to Google Sheets"
NODE_DESCRIPTION = "Write data to a Google Sheets spreadsheet"
NODE_COLOR = "#4caf50"
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
    "sheet_name": {
        "type": "string",
        "title": "Sheet Name",
        "description": "Name of the specific sheet/tab",
        "default": "Sheet1"
    },
    "data": {
        "type": "string",
        "title": "Data",
        "description": "Data to write (array of arrays or reference to data)",
        "required": True
    },
    "insert_mode": {
        "type": "string",
        "title": "Insert Mode",
        "description": "How to insert the data",
        "enum": ["append", "replace", "update"],
        "default": "append"
    },
    "value_input_option": {
        "type": "string",
        "title": "Value Input Option",
        "description": "How to interpret input data",
        "enum": ["RAW", "USER_ENTERED"],
        "default": "USER_ENTERED"
    }
}

def run(config, context):
    """
    Writes data to a Google Sheet
    
    Args:
        config (dict): Configuration for the operation
        context (dict): Shared context from previous nodes
        
    Returns:
        dict: Result information
    """
    credentials_data = config.get('google_credentials', os.environ.get('GOOGLE_CREDENTIALS'))
    spreadsheet_id = config.get('spreadsheet_id')
    sheet_name = config.get('sheet_name', 'Sheet1')
    data_input = config.get('data', [])
    insert_mode = config.get('insert_mode', 'append')
    value_input_option = config.get('value_input_option', 'USER_ENTERED')
    
    if not credentials_data:
        raise ValueError("Google API credentials are required. Either provide them in the configuration or set the GOOGLE_CREDENTIALS environment variable.")
    
    if not spreadsheet_id:
        raise ValueError("Spreadsheet ID is required")
    
    # Process the input data
    if isinstance(data_input, str):
        # Check if it's a reference to context
        if data_input.startswith('{{') and data_input.endswith('}}'):
            # Extract data from context
            path = data_input[2:-2].strip().split('.')
            if path[0] == 'context' and len(path) > 1:
                value = context
                for part in path[1:]:
                    if isinstance(value, dict) and part in value:
                        value = value[part]
                    else:
                        raise ValueError(f"Invalid context path: {data_input}")
                data = value
            else:
                raise ValueError(f"Invalid context reference: {data_input}")
        else:
            # Try to parse as JSON
            try:
                data = json.loads(data_input)
            except json.JSONDecodeError:
                # Treat as string
                data = [[data_input]]
    else:
        # Use as is
        data = data_input
    
    # Ensure data is in the correct format (array of arrays)
    if not isinstance(data, list):
        data = [[data]]
    else:
        # If it's a list of objects, convert to array format with headers
        if data and isinstance(data[0], dict):
            # Extract all possible keys
            all_keys = set()
            for item in data:
                all_keys.update(item.keys())
            
            # Create header row
            header_row = list(all_keys)
            
            # Create data rows
            rows = [header_row]
            for item in data:
                row = [item.get(key, '') for key in header_row]
                rows.append(row)
            
            data = rows
        elif data and not isinstance(data[0], list):
            # Convert simple list to 2D array
            data = [[item] for item in data]
    
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
        
        # Prepare the API request
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Determine API endpoint based on insert mode
        if insert_mode == 'append':
            url = f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{sheet_name}:append?valueInputOption={value_input_option}'
            method = 'POST'
            body = {
                'values': data
            }
        elif insert_mode == 'replace':
            url = f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{sheet_name}?valueInputOption={value_input_option}'
            method = 'PUT'
            body = {
                'values': data
            }
        else:  # update
            # For update, we need to calculate the range based on data size
            num_rows = len(data)
            num_cols = max(len(row) for row in data) if data else 0
            update_range = f'{sheet_name}!A1:{chr(65 + num_cols - 1)}{num_rows}'
            
            url = f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{update_range}?valueInputOption={value_input_option}'
            method = 'PUT'
            body = {
                'values': data
            }
        
        # Make the API request
        if method == 'POST':
            response = requests.post(url, headers=headers, json=body)
        else:  # PUT
            response = requests.put(url, headers=headers, json=body)
        
        # Check response
        if response.status_code in (200, 201):
            result = response.json()
            return {
                'success': True,
                'spreadsheet_id': spreadsheet_id,
                'sheet_name': sheet_name,
                'updated_range': result.get('updatedRange', ''),
                'updated_rows': result.get('updatedRows', 0),
                'updated_columns': result.get('updatedColumns', 0),
                'updated_cells': result.get('updatedCells', 0)
            }
        else:
            error_data = response.json() if response.content else {"error": f"HTTP error {response.status_code}"}
            raise ValueError(f"Google Sheets API error: {error_data}")
    
    except Exception as e:
        raise ValueError(f"Error writing to Google Sheet: {str(e)}")

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
            "scope": "https://www.googleapis.com/auth/spreadsheets",
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