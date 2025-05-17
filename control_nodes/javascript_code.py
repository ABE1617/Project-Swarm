# JavaScript Code Node for Project Swarm
import json

# Node Metadata
NODE_TYPE = "javascript_code"
NODE_NAME = "JavaScript Code"
NODE_DESCRIPTION = "Run JavaScript code (simulated in Python for demonstration)"
NODE_COLOR = "#f48c42"
NODE_ICON = "fa-code"

# Configuration Schema
CONFIG_SCHEMA = {
    "code": {
        "type": "string",
        "title": "Code",
        "description": "JavaScript code to execute (simulated)",
        "required": True
    },
    "input_data": {
        "type": "object",
        "title": "Input Data",
        "description": "Input data for the code"
    }
}

def run(config, context):
    """
    Simulates running JavaScript code (for demonstration purposes only)
    
    Note: This node doesn't actually run JavaScript code as that would require
    a JavaScript runtime integrated with Python. In a real implementation,
    this could use a solution like PyExecJS or a separate Node.js process.
    
    Args:
        config (dict): Configuration including code and input data
        context (dict): Shared context from previous nodes
        
    Returns:
        dict: Simulated execution result
    """
    code = config.get('code', '')
    input_data = config.get('input_data', {})
    
    # In a real implementation, this would execute the JavaScript code
    # Here we just return a simulation result
    
    return {
        'executed': True,
        'code_snippet': code[:100] + ('...' if len(code) > 100 else ''),
        'simulation': 'This node simulates running JavaScript. In a real implementation, it would execute the code.',
        'input_data': input_data
    }
