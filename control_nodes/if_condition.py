# If Condition Node for Project Swarm
import re

# Node Metadata
NODE_TYPE = "if_condition"
NODE_NAME = "If Condition"
NODE_DESCRIPTION = "Branch workflow based on a condition"
NODE_COLOR = "#9c27b0"
NODE_ICON = "fa-code-branch"

# Configuration Schema
CONFIG_SCHEMA = {
    "condition": {
        "type": "string",
        "title": "Condition",
        "description": "Expression to evaluate (e.g., value > 10)",
        "required": True
    },
    "value1": {
        "type": "string",
        "title": "Value 1",
        "description": "First value for comparison"
    },
    "operator": {
        "type": "string",
        "title": "Operator",
        "description": "Comparison operator",
        "enum": ["==", "!=", ">", "<", ">=", "<=", "contains", "startsWith", "endsWith", "isEmpty", "isNotEmpty", "matches"],
        "default": "=="
    },
    "value2": {
        "type": "string",
        "title": "Value 2",
        "description": "Second value for comparison"
    },
    "mode": {
        "type": "string",
        "title": "Condition Mode",
        "description": "How to specify the condition",
        "enum": ["simple", "expression"],
        "default": "simple"
    }
}

def run(config, context):
    """
    Evaluates a condition and determines which branch to follow
    
    Args:
        config (dict): Configuration for the condition
        context (dict): Shared context from previous nodes
        
    Returns:
        dict: Result of the condition evaluation
    """
    mode = config.get('mode', 'simple')
    
    if mode == 'simple':
        # Simple comparison mode
        value1 = config.get('value1', '')
        operator = config.get('operator', '==')
        value2 = config.get('value2', '')
        
        # Process values for context references using {{context.nodeId.key}}
        value1 = process_template(value1, context)
        value2 = process_template(value2, context)
        
        # Convert to appropriate types if possible
        value1 = convert_value(value1)
        value2 = convert_value(value2)
        
        # Evaluate based on operator
        result = evaluate_comparison(value1, operator, value2)
    
    else:  # expression mode
        condition = config.get('condition', '')
        if not condition:
            raise ValueError("Condition expression is required")
        
        # Process the expression with context replacements
        processed_condition = process_template(condition, context)
        
        # Evaluate the expression (basic implementation)
        # In a production system, you'd want a more secure expression evaluator
        try:
            # Simple evaluation of basic expressions
            result = evaluate_expression(processed_condition, context)
        except Exception as e:
            raise ValueError(f"Error evaluating condition: {str(e)}")
    
    # Return the result
    return {
        'result': result,
        'true_path': result,
        'false_path': not result
    }

def process_template(template, context):
    """Process a template string, replacing {{context.nodeId.key}} with actual values"""
    if not isinstance(template, str) or '{{' not in template:
        return template
    
    def replace_context_ref(match):
        path = match.group(1).strip().split('.')
        if path[0] != 'context' or len(path) < 2:
            return match.group(0)  # Return unchanged if not context
        
        # Extract from context
        try:
            value = context
            for part in path[1:]:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return match.group(0)  # Return unchanged if path doesn't exist
            return str(value)
        except:
            return match.group(0)  # Return unchanged on error
    
    return re.sub(r'\{\{(.*?)\}\}', replace_context_ref, template)

def convert_value(value):
    """Convert string value to appropriate type if possible"""
    if not isinstance(value, str):
        return value
    
    # Try to convert to number
    try:
        if '.' in value:
            return float(value)
        else:
            return int(value)
    except ValueError:
        pass
    
    # Check for boolean
    if value.lower() in ('true', 'yes', 'y', '1'):
        return True
    if value.lower() in ('false', 'no', 'n', '0'):
        return False
    
    # Keep as string
    return value

def evaluate_comparison(value1, operator, value2):
    """Evaluate a comparison between two values using the specified operator"""
    if operator == '==':
        return value1 == value2
    elif operator == '!=':
        return value1 != value2
    elif operator == '>':
        return value1 > value2
    elif operator == '<':
        return value1 < value2
    elif operator == '>=':
        return value1 >= value2
    elif operator == '<=':
        return value1 <= value2
    elif operator == 'contains':
        return str(value2) in str(value1)
    elif operator == 'startsWith':
        return str(value1).startswith(str(value2))
    elif operator == 'endsWith':
        return str(value1).endswith(str(value2))
    elif operator == 'isEmpty':
        return value1 is None or value1 == '' or (isinstance(value1, (list, dict)) and len(value1) == 0)
    elif operator == 'isNotEmpty':
        return not (value1 is None or value1 == '' or (isinstance(value1, (list, dict)) and len(value1) == 0))
    elif operator == 'matches':
        try:
            return bool(re.match(str(value2), str(value1)))
        except:
            return False
    else:
        raise ValueError(f"Unknown operator: {operator}")

def evaluate_expression(expression, context):
    """Evaluate a simple expression"""
    # This is a very basic and not secure implementation
    # In a real application, you would use a proper expression parser with security controls
    
    # Replace common operators to make it more JavaScript-like
    expression = expression.replace('&&', ' and ').replace('||', ' or ')
    
    # Very limited safe evaluation - THIS IS NOT SECURE FOR PRODUCTION
    # It's just for demonstration - in a real app, use a proper sandboxed evaluator
    try:
        # Extremely restricted evaluation environment with only basic operations
        safe_dict = {
            'True': True, 
            'False': False, 
            'None': None,
            'and': lambda x, y: x and y,
            'or': lambda x, y: x or y,
            'not': lambda x: not x,
            'context': context
        }
        
        result = eval(expression, {"__builtins__": {}}, safe_dict)
        return bool(result)
    except Exception as e:
        raise ValueError(f"Error evaluating expression: {str(e)}")