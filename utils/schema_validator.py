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

def validate_workflow(workflow_data):
    """
    Validates a workflow against the defined schema
    
    Args:
        workflow_data (dict): The workflow JSON data
        
    Returns:
        tuple: (is_valid, errors) - Boolean indicating if valid and list of errors if any
    """
    try:
        jsonschema.validate(instance=workflow_data, schema=WORKFLOW_SCHEMA)
        return True, []
    except jsonschema.exceptions.ValidationError as e:
        return False, [str(e)]
    
    # Additional custom validation could be added here
    # For example, checking that all connections reference valid node IDs
    
    return True, []
