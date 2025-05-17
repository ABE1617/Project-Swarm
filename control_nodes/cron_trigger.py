# Cron Trigger Node for Project Swarm
import time
import datetime
import re
from croniter import croniter

# Node Metadata
NODE_TYPE = "cron_trigger"
NODE_NAME = "Cron Trigger"
NODE_DESCRIPTION = "Trigger workflow execution based on cron schedule"
NODE_COLOR = "#795548"
NODE_ICON = "fa-calendar-alt"

# Configuration Schema
CONFIG_SCHEMA = {
    "cron_expression": {
        "type": "string",
        "title": "Cron Expression",
        "description": "Cron expression for scheduling (e.g., '0 * * * *' for hourly)",
        "required": True
    },
    "timezone": {
        "type": "string",
        "title": "Timezone",
        "description": "Timezone for the cron schedule",
        "default": "UTC"
    },
    "max_wait": {
        "type": "number",
        "title": "Maximum Wait (seconds)",
        "description": "Maximum time to wait for the next execution",
        "default": 3600  # 1 hour
    },
    "simulation_mode": {
        "type": "boolean",
        "title": "Simulation Mode",
        "description": "When enabled, schedules are calculated but not waited for",
        "default": True
    }
}

def run(config, context):
    """
    Schedules workflow execution based on cron expression
    
    Args:
        config (dict): Configuration for the cron schedule
        context (dict): Shared context from previous nodes
        
    Returns:
        dict: Trigger data including next execution time
    """
    cron_expression = config.get('cron_expression', '')
    if not cron_expression:
        raise ValueError("Cron expression is required")
    
    timezone = config.get('timezone', 'UTC')
    max_wait = float(config.get('max_wait', 3600))
    simulation_mode = config.get('simulation_mode', True)
    
    # Validate the cron expression
    try:
        # Simple validation - check for 5 or 6 fields separated by spaces
        cron_parts = cron_expression.split()
        if len(cron_parts) < 5 or len(cron_parts) > 6:
            raise ValueError("Invalid cron expression format")
        
        # Create croniter object to calculate next execution
        now = datetime.datetime.now(datetime.timezone.utc)
        cron = croniter(cron_expression, now)
        next_execution = cron.get_next(datetime.datetime)
        
        # Calculate seconds until next execution
        wait_seconds = (next_execution - now).total_seconds()
        
    except Exception as e:
        raise ValueError(f"Invalid cron expression: {str(e)}")
    
    # If not in simulation mode and wait time is reasonable, actually wait
    if not simulation_mode and wait_seconds <= max_wait:
        time.sleep(wait_seconds)
        execution_time = datetime.datetime.now(datetime.timezone.utc)
        actual_wait = wait_seconds
        trigger_status = "executed"
    else:
        # In simulation mode or wait too long - don't actually wait
        execution_time = next_execution
        actual_wait = 0
        trigger_status = "simulated" if simulation_mode else "skipped"
    
    # Return information about the trigger
    return {
        'cron_expression': cron_expression,
        'next_execution': next_execution.isoformat(),
        'scheduled_wait': wait_seconds,
        'actual_wait': actual_wait,
        'execution_time': execution_time.isoformat(),
        'trigger_status': trigger_status,
        'timezone': timezone
    }

# Helper function to convert common expressions to cron format
def human_to_cron(expression):
    """Convert human-readable time expressions to cron format"""
    expression = expression.lower().strip()
    
    # Common patterns
    if expression == 'every minute':
        return '* * * * *'
    elif expression == 'every hour':
        return '0 * * * *'
    elif expression == 'every day':
        return '0 0 * * *'
    elif expression == 'every week':
        return '0 0 * * 0'
    elif expression == 'every month':
        return '0 0 1 * *'
    
    # More complex patterns with regex
    minute_pattern = re.compile(r'every (\d+) minutes?')
    hour_pattern = re.compile(r'every (\d+) hours?')
    
    minute_match = minute_pattern.match(expression)
    if minute_match:
        interval = int(minute_match.group(1))
        return f'*/{interval} * * * *'
    
    hour_match = hour_pattern.match(expression)
    if hour_match:
        interval = int(hour_match.group(1))
        return f'0 */{interval} * * *'
    
    # Return original if no match
    return expression