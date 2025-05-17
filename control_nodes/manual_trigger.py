# Manual Trigger Node for Project Swarm
import time

# Node Metadata
NODE_TYPE = "manual_trigger"
NODE_NAME = "Manual Trigger"
NODE_DESCRIPTION = "Start the workflow execution manually"
NODE_COLOR = "#4a69bd"
NODE_ICON = "fa-play-circle"

# Configuration Schema
CONFIG_SCHEMA = {
    "trigger_name": {
        "type": "string",
        "title": "Trigger Name",
        "description": "Name for this trigger point",
        "default": "Start Workflow",
    },
    "description": {
        "type": "string",
        "title": "Description",
        "description": "Optional description of what this workflow does"
    }
}

def run(config, context):
    """
    Serves as the starting point for a workflow
    
    Args:
        config (dict): Configuration for the trigger
        context (dict): Shared context from previous nodes
        
    Returns:
        dict: Basic trigger information
    """
    trigger_name = config.get('trigger_name', 'Start Workflow')
    description = config.get('description', '')
    
    return {
        'trigger_name': trigger_name,
        'description': description,
        'triggered': True,
        'timestamp': time.time(),
        'trigger_id': 'manual'
    }