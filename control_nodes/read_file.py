# Read File Node for Project Swarm
import os
import json
import csv
import base64

# Node Metadata
NODE_TYPE = "read_file"
NODE_NAME = "Read File"
NODE_DESCRIPTION = "Read data from a local file"
NODE_COLOR = "#2196f3"
NODE_ICON = "fa-file-alt"

# Configuration Schema
CONFIG_SCHEMA = {
    "path": {
        "type": "string",
        "title": "File Path",
        "description": "Path to the file (relative to workspace)",
        "required": True
    },
    "format": {
        "type": "string",
        "title": "File Format",
        "description": "How to interpret the file contents",
        "enum": ["auto", "text", "json", "csv", "binary"],
        "default": "auto"
    },
    "encoding": {
        "type": "string",
        "title": "Text Encoding",
        "description": "Character encoding for text files",
        "default": "utf-8"
    },
    "csv_delimiter": {
        "type": "string",
        "title": "CSV Delimiter",
        "description": "Delimiter for CSV files",
        "default": ","
    }
}

def run(config, context):
    """
    Reads data from a file
    
    Args:
        config (dict): Configuration for the file read operation
        context (dict): Shared context from previous nodes
        
    Returns:
        dict: File content and metadata
    """
    path = config.get('path')
    if not path:
        raise ValueError("File path is required")
    
    format_type = config.get('format', 'auto')
    encoding = config.get('encoding', 'utf-8')
    csv_delimiter = config.get('csv_delimiter', ',')
    
    # Ensure the path is within the workspace (security measure)
    abspath = os.path.abspath(path)
    workspace_dir = os.path.abspath('workspace')
    
    # Create a workspace directory if it doesn't exist
    if not os.path.exists(workspace_dir):
        os.makedirs(workspace_dir)
    
    # Make the path relative to workspace if not already
    if not path.startswith('workspace/'):
        file_path = os.path.join(workspace_dir, os.path.basename(path))
    else:
        file_path = path
    
    # Check if file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Detect file format if auto
    if format_type == 'auto':
        file_extension = os.path.splitext(file_path)[1].lower()
        if file_extension in ['.json']:
            format_type = 'json'
        elif file_extension in ['.csv', '.tsv']:
            format_type = 'csv'
            if file_extension == '.tsv':
                csv_delimiter = '\t'
        elif file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.webp', 
                               '.mp3', '.mp4', '.avi', '.mov', '.pdf', '.doc', '.docx',
                               '.xls', '.xlsx', '.zip', '.tar', '.gz', '.exe']:
            format_type = 'binary'
        else:
            format_type = 'text'
    
    # Read file based on format
    result = {'path': file_path}
    
    try:
        if format_type == 'binary':
            with open(file_path, 'rb') as f:
                content = f.read()
                result['content'] = base64.b64encode(content).decode('ascii')
                result['encoding'] = 'base64'
                result['size'] = len(content)
                result['format'] = 'binary'
        
        elif format_type == 'json':
            with open(file_path, 'r', encoding=encoding) as f:
                content = json.load(f)
                result['content'] = content
                result['format'] = 'json'
        
        elif format_type == 'csv':
            with open(file_path, 'r', encoding=encoding, newline='') as f:
                csv_reader = csv.reader(f, delimiter=csv_delimiter)
                rows = list(csv_reader)
                
                # If we have a header row, convert to list of dictionaries
                if len(rows) > 1:
                    header = rows[0]
                    content = []
                    for row in rows[1:]:
                        row_dict = {}
                        for i, cell in enumerate(row):
                            if i < len(header):
                                row_dict[header[i]] = cell
                            else:
                                row_dict[f'column{i+1}'] = cell
                        content.append(row_dict)
                else:
                    content = rows
                
                result['content'] = content
                result['format'] = 'csv'
        
        else:  # text
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
                result['content'] = content
                result['format'] = 'text'
        
        # Add file metadata
        file_stats = os.stat(file_path)
        result['size'] = file_stats.st_size
        result['last_modified'] = file_stats.st_mtime
        
        return result
    
    except Exception as e:
        raise Exception(f"Error reading file {file_path}: {str(e)}")