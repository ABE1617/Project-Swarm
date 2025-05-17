# Merge Node for Project Swarm
import json

# Node Metadata
NODE_TYPE = "merge"
NODE_NAME = "Merge"
NODE_DESCRIPTION = "Combine data from multiple inputs"
NODE_COLOR = "#9c27b0"
NODE_ICON = "fa-object-group"
NODE_INPUTS = ["input1", "input2"]  # Define multiple inputs

# Configuration Schema
CONFIG_SCHEMA = {
    "merge_mode": {
        "type": "string",
        "title": "Merge Mode",
        "description": "How to combine the input data",
        "enum": ["combine", "append", "overwrite"],
        "default": "combine",
        "required": True
    },
    "output_format": {
        "type": "string",
        "title": "Output Format",
        "description": "Format of the merged output",
        "enum": ["object", "array", "string"],
        "default": "object"
    },
    "custom_key": {
        "type": "string",
        "title": "Custom Key",
        "description": "If using object format, the key to use for storing inputs"
    }
}

def run(config, context):
    """
    Merges data from multiple inputs
    
    Args:
        config (dict): Configuration for the merge operation
        context (dict): Shared context from previous nodes
        
    Returns:
        dict: Merged data
    """
    merge_mode = config.get('merge_mode', 'combine')
    output_format = config.get('output_format', 'object')
    custom_key = config.get('custom_key', '')
    
    # Get inputs from incoming connections - in a real implementation, 
    # this would be set by the execution engine based on the connections
    input1 = context.get('input1', {})
    input2 = context.get('input2', {})
    
    # Begin with empty result
    result = {}
    
    # Process based on merge mode
    if merge_mode == 'combine':
        # Combine all inputs into a single object/array
        if output_format == 'object':
            # Merge all object properties
            if isinstance(input1, dict) and isinstance(input2, dict):
                result = {**input1, **input2}
            else:
                # If inputs aren't objects, store them by their source
                result = {
                    'input1': input1,
                    'input2': input2
                }
        
        elif output_format == 'array':
            # Create an array of elements
            result = []
            
            # Add first input
            if isinstance(input1, list):
                result.extend(input1)
            else:
                result.append(input1)
            
            # Add second input
            if isinstance(input2, list):
                result.extend(input2)
            else:
                result.append(input2)
        
        elif output_format == 'string':
            # Convert to strings and concatenate
            result = {
                'combined': str(input1) + str(input2)
            }
    
    elif merge_mode == 'append':
        # Append inputs to an array
        result = []
        
        # Add first input as array if it's already an array
        if isinstance(input1, list):
            result.extend(input1)
        else:
            result.append(input1)
        
        # Add second input similarly
        if isinstance(input2, list):
            result.extend(input2)
        else:
            result.append(input2)
    
    elif merge_mode == 'overwrite':
        # Second input overwrites the first
        result = input2
    
    # If custom key is provided, wrap the result
    if custom_key and output_format != 'string':
        return {custom_key: result}
    
    # For string output format, ensure we return a dict
    if output_format == 'string':
        if isinstance(result, str):
            return {'result': result}
        return result
    
    return {'result': result}