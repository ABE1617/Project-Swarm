# Delay Node for Project Swarm
import time

# Node Metadata
NODE_TYPE = "delay"
NODE_NAME = "Delay"
NODE_DESCRIPTION = "Pause workflow execution for a specified duration"
NODE_COLOR = "#795548"
NODE_ICON = "fa-stopwatch"

# Configuration Schema
CONFIG_SCHEMA = {
    "duration": {
        "type": "number",
        "title": "Duration (seconds)",
        "description": "Time to wait in seconds",
        "default": 5,
        "required": True
    },
    "display_format": {
        "type": "string",
        "title": "Display Format",
        "description": "How to display the duration",
        "enum": ["seconds", "minutes", "hours"],
        "default": "seconds"
    },
    "max_wait": {
        "type": "number",
        "title": "Maximum Wait (seconds)",
        "description": "Maximum time to wait regardless of input",
        "default": 3600  # 1 hour
    }
}

def run(config, context):
    """
    Delays execution for the specified duration
    
    Args:
        config (dict): Configuration for the delay
        context (dict): Shared context from previous nodes
        
    Returns:
        dict: Information about the delay
    """
    duration = float(config.get('duration', 5))
    display_format = config.get('display_format', 'seconds')
    max_wait = float(config.get('max_wait', 3600))  # 1 hour default max
    
    # Convert from display format to seconds
    if display_format == 'minutes':
        seconds = duration * 60
    elif display_format == 'hours':
        seconds = duration * 3600
    else:  # seconds
        seconds = duration
    
    # Cap at maximum wait time
    seconds = min(seconds, max_wait)
    
    # Start time for tracking
    start_time = time.time()
    
    # Perform the delay
    time.sleep(seconds)
    
    # Calculate actual delay (may be slightly different due to processing time)
    actual_time = time.time() - start_time
    
    # Return info about the delay
    return {
        'requested_duration': seconds,
        'actual_duration': actual_time,
        'start_time': start_time,
        'end_time': start_time + actual_time
    }