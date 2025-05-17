import importlib
import logging
import time
import traceback
import json
from datetime import datetime
from collections import defaultdict

# Configure logging
logger = logging.getLogger(__name__)

def build_dependency_graph(workflow_data):
    """Builds a dependency graph from workflow connections"""
    graph = defaultdict(list)
    
    # Extract nodes and connections from workflow
    nodes = {node['id']: node for node in workflow_data.get('nodes', [])}
    connections = workflow_data.get('connections', [])
    
    # Build adjacency list
    for connection in connections:
        source = connection.get('source')
        target = connection.get('target')
        
        if source and target and source in nodes and target in nodes:
            graph[source].append(target)
    
    return graph, nodes

def topological_sort(graph):
    """Performs a topological sort of nodes in the graph"""
    # Initialize variables
    visited = set()
    temp_visited = set()
    order = []
    
    def visit(node):
        """Recursive visit function for DFS"""
        if node in temp_visited:
            # Cyclic dependency detected
            raise ValueError(f"Workflow contains a cycle that includes node {node}")
        
        if node not in visited:
            temp_visited.add(node)
            
            # Visit all dependencies (outgoing edges)
            for neighbor in graph.get(node, []):
                visit(neighbor)
            
            temp_visited.remove(node)
            visited.add(node)
            order.append(node)
    
    # Visit each node
    for node in graph:
        if node not in visited:
            visit(node)
    
    # Find nodes with no outgoing connections (they're not in the graph keys)
    all_nodes = set(graph.keys()).union(*[set(neighbors) for neighbors in graph.values()])
    for node in all_nodes:
        if node not in visited:
            order.append(node)
    
    # Reverse to get correct order (we built it backwards)
    return list(reversed(order))

def execute_workflow(workflow_data):
    """Executes a workflow based on JSON data"""
    # Initialize execution context with debug logs
    execution_context = {
        'start_time': time.time(),
        'debug_logs': [],
        'node_statuses': {},
        'context': {},
        'results': {},
        'errors': [],
        'progress': 0,
        'total_nodes': 0
    }
    
    # Add initial debug log
    add_debug_log(execution_context, 'info', None, "Starting workflow execution")
    
    try:
        # Build dependency graph and get nodes
        graph, nodes = build_dependency_graph(workflow_data)
        
        # Get execution order
        try:
            execution_order = topological_sort(graph)
            add_debug_log(execution_context, 'info', None, f"Execution order determined: {', '.join(execution_order)}")
        except ValueError as e:
            error_msg = f"Error in workflow topology: {str(e)}"
            add_debug_log(execution_context, 'error', None, error_msg)
            raise ValueError(error_msg)
        
        # Set total nodes for progress tracking
        execution_context['total_nodes'] = len(execution_order)
        
        # Initialize all nodes as pending
        for node_id in execution_order:
            execution_context['node_statuses'][node_id] = 'pending'
        
        # Execute each node in order
        for i, node_id in enumerate(execution_order):
            # Update progress
            execution_context['progress'] = int((i / execution_context['total_nodes']) * 100)
            
            node = nodes.get(node_id)
            if not node:
                add_debug_log(execution_context, 'warning', None, 
                             f"Node {node_id} referenced in connections but not defined - skipping")
                continue
            
            node_type = node.get('type')
            node_config = node.get('config', {})
            
            # Mark node as running
            execution_context['node_statuses'][node_id] = 'running'
            add_debug_log(execution_context, 'info', node_id, f"Starting execution of {node_type} node")
            
            node_start_time = time.time()
            
            try:
                # Dynamically import the node module
                module_name = f"control_nodes.{node_type}"
                module = importlib.import_module(module_name)
                
                # Process templates in node config (e.g., {{context.node1.result}})
                processed_config = process_config_templates(node_config, execution_context['context'])
                
                # Add debug log for config (mask sensitive data)
                masked_config = mask_sensitive_data(processed_config)
                add_debug_log(execution_context, 'info', node_id, 
                             f"Configuration: {json.dumps(masked_config, indent=2)}")
                
                # Call the module's run function
                node_result = module.run(processed_config, execution_context['context'])
                
                # Store result in context
                execution_context['context'][node_id] = node_result
                execution_context['results'][node_id] = {
                    'id': node_id,
                    'type': node_type,
                    'status': 'success',
                    'result': node_result,
                    'execution_time': time.time() - node_start_time
                }
                
                # Mark node as successful
                execution_context['node_statuses'][node_id] = 'success'
                add_debug_log(execution_context, 'success', node_id, 
                             f"Execution completed successfully in {time.time() - node_start_time:.3f} seconds")
            
            except ImportError as e:
                error_msg = f"Node type '{node_type}' not found"
                handle_node_error(execution_context, node_id, node_type, error_msg, e, node_start_time)
            
            except Exception as e:
                error_msg = f"Error executing node {node_id}: {str(e)}"
                handle_node_error(execution_context, node_id, node_type, error_msg, e, node_start_time)
        
        # Update final progress
        execution_context['progress'] = 100
        execution_time = time.time() - execution_context['start_time']
        add_debug_log(execution_context, 'success', None, 
                     f"Workflow execution completed in {execution_time:.3f} seconds")
        
    except Exception as e:
        # Handle any other errors in the overall workflow execution
        error_msg = f"Workflow execution failed: {str(e)}"
        add_debug_log(execution_context, 'error', None, error_msg)
        execution_context['errors'].append({
            'message': error_msg,
            'traceback': traceback.format_exc()
        })
    
    # Return the complete execution results including debug logs
    return {
        'nodes': execution_context['results'],
        'context': execution_context['context'],
        'debug_logs': execution_context['debug_logs'],
        'node_statuses': execution_context['node_statuses'],
        'progress': execution_context['progress'],
        'errors': execution_context['errors'],
        'execution_time': time.time() - execution_context['start_time']
    }

def handle_node_error(execution_context, node_id, node_type, error_msg, exception, start_time):
    """Handle errors in node execution with detailed logging"""
    # Log the error
    logger.error(error_msg)
    logger.error(traceback.format_exc())
    
    # Add debug log
    add_debug_log(execution_context, 'error', node_id, error_msg)
    add_debug_log(execution_context, 'error', node_id, f"Traceback: {traceback.format_exc()}")
    
    # Store error details in results
    execution_context['results'][node_id] = {
        'id': node_id,
        'type': node_type,
        'status': 'error',
        'error': error_msg,
        'traceback': traceback.format_exc(),
        'execution_time': time.time() - start_time
    }
    
    # Mark node as failed
    execution_context['node_statuses'][node_id] = 'error'
    
    # Add to errors list
    execution_context['errors'].append({
        'node_id': node_id,
        'message': error_msg,
        'traceback': traceback.format_exc()
    })

def add_debug_log(execution_context, level, node_id, message):
    """Add a debug log entry to the execution context"""
    timestamp = datetime.now().isoformat()
    
    log_entry = {
        'timestamp': timestamp,
        'level': level,
        'node_id': node_id,
        'message': message
    }
    
    execution_context['debug_logs'].append(log_entry)
    
    # Also log to the normal logger
    if level == 'error':
        logger.error(f"{node_id or 'Workflow'}: {message}")
    elif level == 'warning':
        logger.warning(f"{node_id or 'Workflow'}: {message}")
    elif level == 'success':
        logger.info(f"{node_id or 'Workflow'}: {message}")
    else:
        logger.info(f"{node_id or 'Workflow'}: {message}")

def mask_sensitive_data(data):
    """Mask sensitive fields in configuration data for logging"""
    if not isinstance(data, dict):
        return data
    
    masked_data = data.copy()
    sensitive_keys = ['api_key', 'password', 'secret', 'token', 'credentials', 'auth']
    
    for key, value in masked_data.items():
        # Check if this key contains any sensitive words
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            if isinstance(value, str) and value:
                # Mask all but first and last 3 characters
                if len(value) > 8:
                    masked_data[key] = value[:3] + '*' * (len(value) - 6) + value[-3:]
                else:
                    masked_data[key] = '****'
        # Recursively mask nested dictionaries
        elif isinstance(value, dict):
            masked_data[key] = mask_sensitive_data(value)
        # Mask items in lists if they are dictionaries
        elif isinstance(value, list):
            masked_data[key] = [mask_sensitive_data(item) if isinstance(item, dict) else item for item in value]
    
    return masked_data

def process_config_templates(config, context):
    """Process config values that contain template placeholders"""
    if isinstance(config, dict):
        return {k: process_config_templates(v, context) for k, v in config.items()}
    elif isinstance(config, list):
        return [process_config_templates(item, context) for item in config]
    elif isinstance(config, str) and '{{' in config and '}}' in config:
        # Handle template syntax {{context.nodeId.key}}
        try:
            # Simple template processing (for more complex needs, consider a template engine)
            import re
            
            def replace_template(match):
                path = match.group(1).strip().split('.')
                if path[0] != 'context' or len(path) < 3:
                    return match.group(0)  # Return unchanged if not starting with context
                
                # Extract from context
                node_id = path[1]
                key = '.'.join(path[2:])  # Handle nested keys
                
                if node_id not in context:
                    return f"[Node {node_id} not found]"
                
                # Navigate to the value
                value = context[node_id]
                for part in key.split('.'):
                    if isinstance(value, dict) and part in value:
                        value = value[part]
                    else:
                        return f"[Key {key} not found in node {node_id}]"
                
                return str(value)
            
            return re.sub(r'{{(.*?)}}', replace_template, config)
        
        except Exception as e:
            logger.error(f"Error processing template in config: {str(e)}")
            return config
    else:
        return config
