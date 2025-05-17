# Set Variable Node for Project Swarm
import json

# Node Metadata
NODE_TYPE = "set_variable"
NODE_NAME = "Set Variable"
NODE_DESCRIPTION = "Define a variable to be used in the workflow"
NODE_COLOR = "#9c27b0"
NODE_ICON = "fa-database"

# Configuration Schema
CONFIG_SCHEMA = {
    "name": {
        "type": "string",
        "title": "Variable Name",
        "description": "Name of the variable to set",
        "required": True
    },
    "value": {
        "type": "string",
        "title": "Value",
        "description": "Value to assign to the variable",
        "required": True
    },
    "type": {
        "type": "string",
        "title": "Value Type",
        "description": "How to interpret the value",
        "enum": ["string", "number", "boolean", "json", "expression"],
        "default": "string",
        "required": True
    },
    "scope": {
        "type": "string",
        "title": "Variable Scope",
        "description": "Where the variable can be accessed",
        "enum": ["workflow", "node"],
        "default": "workflow",
        "required": True
    }
}

def run(config, context):
    """
    Sets a variable value in the workflow context
    
    Args:
        config (dict): Configuration for the variable
        context (dict): Shared context from previous nodes
        
    Returns:
        dict: Variable data
    """
    var_name = config.get('name', '')
    var_value = config.get('value', '')
    var_type = config.get('type', 'string')
    var_scope = config.get('scope', 'workflow')
    
    if not var_name:
        raise ValueError("Variable name is required")
    
    # Process the value based on type
    if var_type == 'number':
        try:
            if '.' in var_value:
                processed_value = float(var_value)
            else:
                processed_value = int(var_value)
        except ValueError:
            raise ValueError(f"Cannot convert '{var_value}' to a number")
    
    elif var_type == 'boolean':
        if var_value.lower() in ['true', 'yes', '1', 'y']:
            processed_value = True
        elif var_value.lower() in ['false', 'no', '0', 'n']:
            processed_value = False
        else:
            raise ValueError(f"Cannot convert '{var_value}' to a boolean")
    
    elif var_type == 'json':
        try:
            processed_value = json.loads(var_value)
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON: {var_value}")
    
    elif var_type == 'expression':
        # Simple expression evaluation - this is a basic implementation
        # In a real-world app, you'd want a more robust and secure expression evaluator
        try:
            # Very simple replacement of context references
            import re
            
            def replace_context_ref(match):
                path = match.group(1).split('.')
                if path[0] == 'context' and len(path) > 1:
                    value = context
                    for part in path[1:]:
                        if isinstance(value, dict) and part in value:
                            value = value[part]
                        else:
                            return match.group(0)  # Leave unchanged if path doesn't exist
                    return str(value)
                return match.group(0)
            
            processed_value = re.sub(r'\{\{(.*?)\}\}', replace_context_ref, var_value)
        except Exception as e:
            raise ValueError(f"Error evaluating expression: {str(e)}")
    
    else:  # string or default
        processed_value = var_value
    
    # Store in the appropriate scope
    if var_scope == 'workflow':
        # For workflow scope, we store in the 'variables' key of the context
        if 'variables' not in context:
            context['variables'] = {}
        context['variables'][var_name] = processed_value
    
    # For node scope, the value is just returned in the node's output
    
    # Return the variable information
    return {
        'name': var_name,
        'value': processed_value,
        'type': var_type,
        'scope': var_scope
    }