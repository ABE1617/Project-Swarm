# Write File Node for Project Swarm
import os
import csv
import json

# Node Metadata
NODE_TYPE = "write_file"
NODE_NAME = "Write File"
NODE_DESCRIPTION = "Write data to a file on the server"
NODE_COLOR = "#4caf50"
NODE_ICON = "fa-file"

# Configuration Schema
CONFIG_SCHEMA = {
    "file_format": {
        "type": "string",
        "title": "File Format",
        "description": "Choose the file format to save (txt or csv)",
        "enum": ["txt", "csv"],
        "default": "txt",
        "required": True
    },
    "file_name": {
        "type": "string",
        "title": "File Name",
        "description": "Name of the output file (e.g. output.txt or output.csv)",
        "required": True
    },
    "folder_path": {
        "type": "string",
        "title": "Folder Path",
        "description": "Destination folder for the file. You can type or use the Choose Folder button.",
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
    Writes data to a file (txt or csv) in the specified folder with the specified name.
    """
    file_format = config.get('file_format', 'txt')
    file_name = config.get('file_name')
    folder_path = config.get('folder_path')
    content = config.get('content', '')
    mode = config.get('mode', 'overwrite')
    create_dirs = config.get('create_directories', True)

    if not file_name:
        raise ValueError("File name is required")
    if not folder_path:
        raise ValueError("Folder path is required")

    # Ensure the folder path is within the workspace (security measure)
    workspace_dir = os.path.abspath('workspace')
    abs_folder = os.path.abspath(os.path.join(workspace_dir, folder_path))
    if not abs_folder.startswith(workspace_dir):
        raise ValueError("Invalid folder path")

    # Create directory if needed
    if create_dirs and not os.path.exists(abs_folder):
        os.makedirs(abs_folder)

    # Full file path
    full_path = os.path.join(abs_folder, file_name)

    # Write to file
    write_mode = 'a' if mode == 'append' else 'w'
    if file_format == 'csv':
        # Try to parse content as JSON/array
        try:
            data = json.loads(content)
        except Exception:
            raise ValueError("Content must be a valid JSON array for CSV format")
        if not isinstance(data, list):
            raise ValueError("Content must be a list of rows for CSV format")
        with open(full_path, write_mode, newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            for row in data:
                if isinstance(row, dict):
                    # Write header if first row
                    if f.tell() == 0:
                        writer.writerow(row.keys())
                    writer.writerow(row.values())
                elif isinstance(row, list):
                    writer.writerow(row)
                else:
                    writer.writerow([row])
    else:
        with open(full_path, write_mode, encoding='utf-8') as f:
            f.write(content)

    return {
        'path': full_path,
        'size': os.path.getsize(full_path),
        'success': True
    }
