# Wait Node for Project Swarm
import time

# Node Metadata
NODE_TYPE = "wait"
NODE_NAME = "Wait"
NODE_DESCRIPTION = "Pause workflow execution for a specified duration"
NODE_COLOR = "#9c27b0"
NODE_ICON = "fa-hourglass-half"

# Configuration Schema
CONFIG_SCHEMA = {
    "duration": {
        "type": "number",
        "title": "Duration",
        "description": "Time to wait",
        "default": 5,
        "required": True
    },
    "unit": {
        "type": "string",
        "title": "Time Unit",
        "description": "Unit of time for the duration",
        "enum": ["seconds", "minutes", "hours"],
        "default": "seconds",
        "required": True
    },
    "max_wait": {
        "type": "number",
        "title": "Maximum Wait",
        "description": "Maximum time to wait (in seconds)",
        "default": 3600  # 1 hour default max
    }
}

def run(config, context):
    """
    Pauses workflow execution for the specified time
    
    Args:
        config (dict): Configuration for the wait operation
        context (dict): Shared context from previous nodes
        
    Returns:
        dict: Wait operation information
    """
    duration = float(config.get('duration', 5))
    unit = config.get('unit', 'seconds')
    max_wait = float(config.get('max_wait', 3600))  # 1 hour default max
    
    # Convert to seconds based on the unit
    seconds = duration
    if unit == 'minutes':
        seconds = duration * 60
    elif unit == 'hours':
        seconds = duration * 3600
    
    # Cap at maximum wait time
    seconds = min(seconds, max_wait)
    
    # Record the start time
    start_time = time.time()
    
    # Perform the wait operation
    time.sleep(seconds)
    
    # Return wait information
    end_time = time.time()
    actual_duration = end_time - start_time
    
    return {
        'requested_duration': seconds,
        'actual_duration': actual_duration,
        'unit': 'seconds',
        'start_time': start_time,
        'end_time': end_time
    }