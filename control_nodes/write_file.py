# Write File Node for Project Swarm
import os

# Node Metadata
NODE_TYPE = "write_file"
NODE_NAME = "Write File"
NODE_DESCRIPTION = "Write data to a file on the server"
NODE_COLOR = "#4caf50"
NODE_ICON = "fa-file"

# Configuration Schema
CONFIG_SCHEMA = {
    "path": {
        "type": "string",
        "title": "File Path",
        "description": "Path to write the file (relative to workspace)",
        "required": True
    },
    "content": {
        "type": "string",
        "title": "Content",
        "description": "Content to write to the file",
        "required": True
    },
    "mode": {
        "type": "string",
        "title": "Write Mode",
        "description": "File write mode",
        "enum": ["overwrite", "append"],
        "default": "overwrite"
    },
    "create_directories": {
        "type": "boolean",
        "title": "Create Directories",
        "description": "Create directories in the path if they don't exist",
        "default": True
    }
}

def run(config, context):
    """
    Writes data to a file
    
    Args:
        config (dict): Configuration for the file write operation
        context (dict): Shared context from previous nodes
        
    Returns:
        dict: Result of the operation
    """
    path = config.get('path')
    if not path:
        raise ValueError("File path is required")
    
    content = config.get('content', '')
    mode = config.get('mode', 'overwrite')
    create_dirs = config.get('create_directories', True)
    
    # Ensure the path is within the workspace (security measure)
    abspath = os.path.abspath(path)
    workspace_dir = os.path.abspath('workspace')
    
    # Create a workspace directory if it doesn't exist
    if not os.path.exists(workspace_dir):
        os.makedirs(workspace_dir)
    
    # Make the path relative to workspace for security
    rel_path = os.path.join(workspace_dir, os.path.basename(path))
    
    # Create directory if needed
    if create_dirs:
        directory = os.path.dirname(rel_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
    
    # Write to file
    write_mode = 'a' if mode == 'append' else 'w'
    with open(rel_path, write_mode) as f:
        f.write(content)
    
    # Return result
    return {
        'path': rel_path,
        'size': os.path.getsize(rel_path),
        'success': True
    }
