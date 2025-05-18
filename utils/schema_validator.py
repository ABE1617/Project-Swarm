import jsonschema

# Define the workflow schema
WORKFLOW_SCHEMA = {
    "type": "object",
    "required": ["nodes"],
    "properties": {
        "nodes": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "type"],
                "properties": {
                    "id": {"type": "string"},
                    "type": {"type": "string"},
                    "config": {"type": "object"}
                }
            }
        },
        "connections": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["source", "target"],
                "properties": {
                    "source": {"type": "string"},
                    "target": {"type": "string"}
                }
            }
        },
        "variables": {
            "type": "object"
        }
    }
}

# List of node types that can only have one input connection
SINGLE_INPUT_NODES = [
    "http_request", "write_file", "read_file", "email_send", "gmail_send", 
    "save_to_sheets", "save_to_drive", "webhook_response", "set_variable",
    "wait", "data_transform"
]

# List of node types that can serve as workflow triggers
TRIGGER_NODE_TYPES = [
    "manual_trigger", "webhook_trigger", "schedule_trigger", "email_trigger", "file_trigger"
]

def validate_workflow(workflow_data):
    """
    Validates a workflow against the defined schema and additional custom rules
    
    Args:
        workflow_data (dict): The workflow JSON data
        
    Returns:
        tuple: (is_valid, errors) - Boolean indicating if valid and list of errors if any
    """
    errors = []
    
    # Basic schema validation
    try:
        jsonschema.validate(instance=workflow_data, schema=WORKFLOW_SCHEMA)
    except jsonschema.exceptions.ValidationError as e:
        return False, [str(e)]
    
    # Additional custom validation
    # Get nodes and connections
    nodes = {node["id"]: node for node in workflow_data.get("nodes", [])}
    connections = workflow_data.get("connections", [])
    
    # Check if workflow has at least one node
    if not nodes:
        errors.append("Workflow must contain at least one node")
        return False, errors
    
    # Build input connection counts for each node
    input_connections = {}
    for conn in connections:
        target = conn.get("target")
        if target in nodes:
            input_connections[target] = input_connections.get(target, 0) + 1
    
    # Check nodes that should have only one input
    for node_id, node in nodes.items():
        if node["type"] in SINGLE_INPUT_NODES and input_connections.get(node_id, 0) > 1:
            errors.append(f"Node '{node_id}' ({node['type']}) can only have one input connection")
    
    # Check required configuration fields
    for node_id, node in nodes.items():
        node_type = node["type"]
        config = node.get("config", {})
        
        # HTTP Request node requires URL
        if node_type == "http_request" and not config.get("url"):
            errors.append(f"Node '{node_id}' (HTTP Request) requires a URL")
        
        # Email nodes require to, subject, and body
        elif node_type == "email_send":
            for field in ["to", "subject", "body"]:
                if not config.get(field):
                    errors.append(f"Node '{node_id}' (Email Send) requires '{field}'")
        
        # File operations require path
        elif node_type in ["write_file", "read_file"] and not config.get("path"):
            errors.append(f"Node '{node_id}' ({node_type}) requires a file path")
            
        # Write file needs content
        elif node_type == "write_file" and not config.get("content"):
            errors.append(f"Node '{node_id}' (Write File) requires content")
    
    is_valid = len(errors) == 0
    return is_valid, errors
