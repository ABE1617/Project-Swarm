# Data Transform Node for Project Swarm
import json

# Node Metadata
NODE_TYPE = "data_transform"
NODE_NAME = "Data Transform"
NODE_DESCRIPTION = "Transform, filter and manipulate data"
NODE_COLOR = "#ff9800"
NODE_ICON = "fa-filter"

# Configuration Schema
CONFIG_SCHEMA = {
    "operation": {
        "type": "string",
        "title": "Operation",
        "description": "Type of transformation to perform",
        "enum": ["filter", "map", "sort", "select", "custom"],
        "default": "filter",
        "required": True
    },
    "input": {
        "type": "string",
        "title": "Input",
        "description": "Path to the input data in context (e.g., nodeId.response)",
        "required": True
    },
    "filter_condition": {
        "type": "string", 
        "title": "Filter Condition",
        "description": "JavaScript-like condition for filtering (e.g., 'item.age > 18')",
        "showIf": {
            "operation": "filter"
        }
    },
    "map_expression": {
        "type": "string",
        "title": "Map Expression",
        "description": "Expression for mapping (e.g., '{name: item.name, age: item.age}')",
        "showIf": {
            "operation": "map"
        }
    },
    "sort_key": {
        "type": "string",
        "title": "Sort Key",
        "description": "Key to sort by (e.g., 'name')",
        "showIf": {
            "operation": "sort"
        }
    },
    "sort_descending": {
        "type": "boolean",
        "title": "Sort Descending",
        "description": "Sort in descending order",
        "default": False,
        "showIf": {
            "operation": "sort"
        }
    },
    "select_keys": {
        "type": "array",
        "title": "Select Keys",
        "description": "List of keys to select from objects",
        "showIf": {
            "operation": "select"
        }
    },
    "custom_code": {
        "type": "string",
        "title": "Custom Code",
        "description": "Custom Python code to transform data (returns a processed version of the input)",
        "showIf": {
            "operation": "custom"
        }
    }
}

def run(config, context):
    """
    Transforms data based on the specified operation
    
    Args:
        config (dict): Configuration for the transformation
        context (dict): Shared context from previous nodes
        
    Returns:
        dict: Transformed data
    """
    operation = config.get('operation', 'filter')
    input_path = config.get('input', '')
    
    if not input_path:
        raise ValueError("Input path is required")
    
    # Extract input data from context
    input_parts = input_path.split('.')
    if len(input_parts) < 2:
        raise ValueError("Input path must be in format 'nodeId.key.subkey'")
    
    node_id = input_parts[0]
    if node_id not in context:
        raise ValueError(f"Node {node_id} not found in context")
    
    value = context[node_id]
    for part in input_parts[1:]:
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            raise ValueError(f"Key {part} not found in {input_path}")
    
    # Input data to transform
    input_data = value
    
    # Perform transformation based on operation
    if operation == 'filter':
        condition = config.get('filter_condition', '')
        if not condition:
            raise ValueError("Filter condition is required for filter operation")
        
        # Simple filter implementation (for complex needs, consider exec/eval with proper safety)
        # This is a simplified simulation of JavaScript's filter
        result = []
        if isinstance(input_data, list):
            for item in input_data:
                # Very simple condition evaluation (limited to a few operations)
                if eval_simple_condition(condition, item):
                    result.append(item)
        else:
            raise ValueError("Filter operation requires a list input")
    
    elif operation == 'map':
        expression = config.get('map_expression', '')
        if not expression:
            raise ValueError("Map expression is required for map operation")
        
        # Simple map implementation
        result = []
        if isinstance(input_data, list):
            for item in input_data:
                # This is just a simulation - in a real implementation,
                # you would use a more sophisticated expression evaluator
                mapped_item = eval_simple_mapping(expression, item)
                result.append(mapped_item)
        else:
            raise ValueError("Map operation requires a list input")
    
    elif operation == 'sort':
        sort_key = config.get('sort_key', '')
        descending = config.get('sort_descending', False)
        
        if not sort_key:
            raise ValueError("Sort key is required for sort operation")
        
        # Sort the list
        if isinstance(input_data, list):
            # Check if all items have the sort_key
            if not all(isinstance(item, dict) and sort_key in item for item in input_data):
                raise ValueError(f"Not all items have the sort key '{sort_key}'")
            
            result = sorted(input_data, key=lambda x: x[sort_key], reverse=descending)
        else:
            raise ValueError("Sort operation requires a list input")
    
    elif operation == 'select':
        select_keys = config.get('select_keys', [])
        
        if not select_keys:
            raise ValueError("Select keys are required for select operation")
        
        # Select specific keys from each object
        result = []
        if isinstance(input_data, list):
            for item in input_data:
                if isinstance(item, dict):
                    result.append({k: item.get(k) for k in select_keys if k in item})
                else:
                    result.append(item)  # Non-dict items are passed through
        elif isinstance(input_data, dict):
            result = {k: input_data.get(k) for k in select_keys if k in input_data}
        else:
            raise ValueError("Select operation requires a list or dict input")
    
    elif operation == 'custom':
        custom_code = config.get('custom_code', '')
        if not custom_code:
            raise ValueError("Custom code is required for custom operation")
        
        # For safety, in a real implementation you would use a sandboxed environment
        # Here we simulate it with a simple wrapper
        result = simulate_custom_code(custom_code, input_data)
    
    else:
        raise ValueError(f"Unknown operation: {operation}")
    
    return {
        'result': result,
        'operation': operation,
        'input_size': len(input_data) if isinstance(input_data, (list, dict)) else 1,
        'output_size': len(result) if isinstance(result, (list, dict)) else 1
    }

def eval_simple_condition(condition, item):
    """
    Evaluates a simple condition on an item (simulated)
    
    Very limited implementation for demonstration purposes only.
    In a real implementation, you would use a more robust solution.
    """
    # This is highly simplified and not secure for production use
    # Only support a few common comparisons
    try:
        # Replace "item." with a dictionary lookup
        condition = condition.replace('item.', 'item["').replace(' ', '"] ')
        condition = condition.replace('==', '"] ==').replace('!=', '"] !=')
        condition = condition.replace('>', '"] >').replace('<', '"] <')
        condition = condition.replace('>=', '"] >=').replace('<=', '"] <=')
        
        # Extremely basic evaluation - ONLY FOR DEMONSTRATION
        # In a real app, you would use a proper expression parser with security controls
        return eval(condition, {"item": item})
    except Exception as e:
        raise ValueError(f"Error evaluating condition: {str(e)}")

def eval_simple_mapping(expression, item):
    """
    Evaluates a simple mapping expression (simulated)
    
    Very limited implementation for demonstration purposes only.
    """
    # This is highly simplified and not secure for production use
    try:
        # Convert JavaScript-like syntax to Python dict syntax
        # Only handle the most basic case for demonstration
        result = {}
        
        # Strip braces and split by commas
        if expression.startswith('{') and expression.endswith('}'):
            expression = expression[1:-1]
        
        parts = expression.split(',')
        for part in parts:
            if ':' in part:
                key, value = part.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                # Simple replacement of item.property with dict lookup
                if 'item.' in value:
                    prop = value.split('item.')[1]
                    result[key] = item.get(prop)
                else:
                    # Try to eval as literal
                    try:
                        result[key] = eval(value)
                    except:
                        result[key] = value
        
        return result
    except Exception as e:
        raise ValueError(f"Error evaluating mapping expression: {str(e)}")

def simulate_custom_code(code, input_data):
    """
    Simulates running custom code (sanitized for security)
    
    In a real implementation, you would use a proper sandboxing solution.
    """
    # This is just a simulation of executing custom code
    # For demonstration purposes only
    return {
        "result": "Custom code execution simulated",
        "input_data": input_data,
        "code_preview": code[:100] + ("..." if len(code) > 100 else ""),
        "note": "In a real implementation, this would execute properly sandboxed Python code"
    }
