import importlib
import logging
import time
import traceback
import json
from datetime import datetime
from collections import defaultdict
import sys

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('workflow_execution.log')
    ]
)
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

def identify_connected_nodes(graph, nodes):
    """Identifies all nodes that are connected to the workflow (reachable from triggers)"""
    # All nodes in the graph (sources and targets)
    all_nodes = set(graph.keys())
    for targets in graph.values():
        all_nodes.update(targets)
        
    # Find nodes with no incoming connections (triggers or orphaned nodes)
    # We'll treat these as starting points
    incoming_connections = set()
    for source, targets in graph.items():
        incoming_connections.update(targets)
    
    # Identify starting nodes as only explicit trigger nodes
    from utils.schema_validator import TRIGGER_NODE_TYPES
    starting_nodes = {node_id for node_id, node in nodes.items() if node.get('type') in TRIGGER_NODE_TYPES}
    
    # Perform DFS from each starting node to find all reachable nodes
    visited = set()
    
    def dfs(node):
        if node in visited:
            return
        visited.add(node)
        for neighbor in graph.get(node, []):
            dfs(neighbor)
    
    # Start DFS from each starting node
    for node in starting_nodes:
        dfs(node)
    
    return visited

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

def add_debug_log(context, level, node_id, message):
    """Adds a debug log entry to the execution context"""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'level': level,
        'node_id': node_id,
        'message': message
    }
    context['debug_logs'].append(log_entry)
    
    # Also log to system logs
    if level == 'error':
        logger.error(f"[Node {node_id}] {message}")
    elif level == 'warning':
        logger.warning(f"[Node {node_id}] {message}")
    else:
        logger.info(f"[Node {node_id}] {message}")

def mask_sensitive_data(data):
    """Masks sensitive data in logs (passwords, tokens, etc.)"""
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            if key.lower() in ['password', 'token', 'api_key', 'secret', 'auth', 'credential', 'private_key']:
                result[key] = '*****'
            else:
                result[key] = mask_sensitive_data(value)
        return result
    elif isinstance(data, list):
        return [mask_sensitive_data(item) for item in data]
    else:
        return data

def process_config_templates(config, context):
    """Processes templates in configuration values (e.g., {{context.nodeId.result}})"""
    # Process string templates
    if isinstance(config, str):
        # TODO: Implement template parsing for strings
        return config
    
    # Process dictionaries recursively
    if isinstance(config, dict):
        processed_config = {}
        for key, value in config.items():
            processed_config[key] = process_config_templates(value, context)
        return processed_config
    
    # Process lists recursively
    if isinstance(config, list):
        return [process_config_templates(item, context) for item in config]
    
    # Return other types as-is
    return config

def handle_node_error(context, node_id, node_type, message, exception, start_time):
    """Handles node execution errors uniformly"""
    # Add error to debug logs
    add_debug_log(context, 'error', node_id, message)
    
    # Add traceback for detailed debugging
    add_debug_log(context, 'error', node_id, f"Traceback: {traceback.format_exc()}")
    
    # Record error in results
    context['results'][node_id] = {
        'id': node_id,
        'type': node_type,
        'status': 'error',
        'error': str(exception),
        'execution_time': time.time() - start_time
    }
    
    # Add to errors list
    context['errors'].append({
        'node_id': node_id,
        'message': message,
        'details': str(exception),
        'traceback': traceback.format_exc(),
        'timestamp': datetime.now().isoformat()
    })
    
    # Mark node status as failed
    context['node_statuses'][node_id] = 'error'

def format_execution_results(context):
    """Formats execution results for API response"""
    return {
        'execution_time': time.time() - context['start_time'],
        'debug_logs': context['debug_logs'],
        'node_statuses': context['node_statuses'],
        'results': context['results'],
        'errors': context['errors'],
        'progress': context['progress']
    }

def resolve_execution_order_with_positions(graph, nodes):
    """
    Determines execution order considering both dependencies and visual left-to-right positions
    
    This ensures that when multiple nodes are at the same dependency level,
    they execute from left to right as shown in the UI.
    """
    # Get base topological sort order (based on dependencies)
    base_order = topological_sort(graph)
    
    # Group nodes by their levels in the dependency graph
    levels = {}
    node_levels = {}
    
    # First, find all starting nodes (no incoming edges)
    incoming_edges = set()
    for source, targets in graph.items():
        for target in targets:
            incoming_edges.add(target)
    
    starting_nodes = set(base_order) - incoming_edges
    
    # Assign levels through BFS
    current_level = 0
    current_nodes = starting_nodes
    visited = set()
    
    while current_nodes:
        levels[current_level] = list(current_nodes)
        next_level_nodes = set()
        
        for node in current_nodes:
            node_levels[node] = current_level
            visited.add(node)
            
            # Add all unvisited neighbors to the next level
            for neighbor in graph.get(node, []):
                if neighbor not in visited and neighbor not in next_level_nodes:
                    # Check if all prerequisites are visited
                    prereqs_visited = True
                    for source, targets in graph.items():
                        if neighbor in targets and source not in visited:
                            prereqs_visited = False
                            break
                    
                    if prereqs_visited:
                        next_level_nodes.add(neighbor)
        
        current_nodes = next_level_nodes
        current_level += 1
    
    # Sort nodes at each level by their x-position (left to right)
    for level, level_nodes in levels.items():
        # Sort nodes at this level by x position
        level_nodes.sort(key=lambda node_id: nodes.get(node_id, {}).get('position', {}).get('x', 0))
    
    # Rebuild execution order based on levels
    execution_order = []
    for level in sorted(levels.keys()):
        execution_order.extend(levels[level])
    
    # Handle any nodes not yet placed (should rarely happen)
    for node in base_order:
        if node not in execution_order:
            execution_order.append(node)
    
    return execution_order

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
        'total_nodes': 0,
        'workflow_id': workflow_data.get('id', 'unknown'),
        'workflow_name': workflow_data.get('name', 'unknown')
    }
    
    # Add initial debug logs
    add_debug_log(execution_context, 'info', None, f"Starting workflow execution - ID: {execution_context['workflow_id']}, Name: {execution_context['workflow_name']}")
    add_debug_log(execution_context, 'info', None, f"Workflow configuration: {json.dumps(mask_sensitive_data(workflow_data), indent=2)}")
    
    try:
        # Check if workflow has nodes
        if not workflow_data.get('nodes'):
            error_msg = "Workflow contains no nodes"
            add_debug_log(execution_context, 'error', None, error_msg)
            execution_context['errors'].append({
                'message': error_msg,
                'timestamp': datetime.now().isoformat()
            })
            return format_execution_results(execution_context)
            
        # Find trigger nodes (manual or other types) - for logging purposes only
        from utils.schema_validator import TRIGGER_NODE_TYPES
        trigger_nodes = [node for node in workflow_data.get('nodes', []) if node.get('type') in TRIGGER_NODE_TYPES]
        
        if trigger_nodes:
            add_debug_log(execution_context, 'info', None, f"Found {len(trigger_nodes)} trigger nodes")
        else:
            add_debug_log(execution_context, 'warning', None, "No trigger nodes found in workflow")
            
        # Build dependency graph and get nodes
        try:
            graph, nodes = build_dependency_graph(workflow_data)
            add_debug_log(execution_context, 'info', None, 
                         f"Built dependency graph with {len(nodes)} nodes. Node types: " + 
                         json.dumps({node_id: node['type'] for node_id, node in nodes.items()}))
        except Exception as e:
            error_msg = f"Error building dependency graph: {str(e)}"
            add_debug_log(execution_context, 'error', None, error_msg)
            execution_context['errors'].append({
                'message': error_msg,
                'traceback': traceback.format_exc(),
                'timestamp': datetime.now().isoformat()
            })
            return format_execution_results(execution_context)
        
        # Find all connected nodes (reachable from triggers)
        connected_nodes = identify_connected_nodes(graph, nodes)
        
        # Filter out unconnected nodes
        # Keep only nodes that are reachable from triggers
        reachable_nodes = {}
        for node_id, node in nodes.items():
            if node_id in connected_nodes or node.get('type') in TRIGGER_NODE_TYPES:
                reachable_nodes[node_id] = node
        
        # Log how many nodes were filtered out
        if len(nodes) != len(reachable_nodes):
            filtered_nodes = set(nodes.keys()) - set(reachable_nodes.keys())
            add_debug_log(execution_context, 'info', None, 
                         f"Filtered out {len(filtered_nodes)} unconnected nodes: {', '.join(filtered_nodes)}")
            
            # Update graph to include only connected nodes
            filtered_graph = defaultdict(list)
            for source, targets in graph.items():
                if source in reachable_nodes:
                    filtered_graph[source] = [target for target in targets if target in reachable_nodes]
            
            graph = filtered_graph
            nodes = reachable_nodes
            
        # Get execution order considering node positions (left-to-right UI order)
        try:
            # Check if nodes have position data
            has_position_data = any('position' in node for node in nodes.values())
            
            if has_position_data:
                execution_order = resolve_execution_order_with_positions(graph, nodes)
                add_debug_log(execution_context, 'info', None, 
                             f"Execution order determined with left-to-right positioning: {', '.join(execution_order)}")
            else:
                # Fall back to basic topological sort if no position data
                execution_order = topological_sort(graph)
                add_debug_log(execution_context, 'info', None, 
                             f"Execution order determined with dependencies only: {', '.join(execution_order)}")
                
        except ValueError as e:
            error_msg = f"Error in workflow topology: {str(e)}"
            add_debug_log(execution_context, 'error', None, error_msg)
            execution_context['errors'].append({
                'message': error_msg,
                'traceback': traceback.format_exc(),
                'timestamp': datetime.now().isoformat()
            })
            return format_execution_results(execution_context)
        
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
                try:
                    module_name = f"control_nodes.{node_type}"
                    module = importlib.import_module(module_name)
                except ImportError as e:
                    error_msg = f"Node type '{node_type}' not found or could not be imported"
                    handle_node_error(execution_context, node_id, node_type, error_msg, e, node_start_time)
                    continue
                
                # Process templates in node config (e.g., {{context.node1.result}})
                try:
                    processed_config = process_config_templates(node_config, execution_context['context'])
                except Exception as e:
                    error_msg = f"Error processing configuration templates: {str(e)}"
                    handle_node_error(execution_context, node_id, node_type, error_msg, e, node_start_time)
                    continue
                
                # Add debug log for config (mask sensitive data)
                masked_config = mask_sensitive_data(processed_config)
                add_debug_log(execution_context, 'info', node_id, 
                             f"Configuration: {json.dumps(masked_config, indent=2)}")
                
                # Call the module's run function
                try:
                    if not hasattr(module, 'run'):
                        error_msg = f"Node type '{node_type}' does not implement required 'run' function"
                        handle_node_error(execution_context, node_id, node_type, error_msg, 
                                         AttributeError(error_msg), node_start_time)
                        continue
                    
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
                except Exception as e:
                    error_msg = f"Error executing node {node_id}: {str(e)}"
                    handle_node_error(execution_context, node_id, node_type, error_msg, e, node_start_time)
            
            except Exception as e:
                error_msg = f"Unexpected error in node {node_id}: {str(e)}"
                handle_node_error(execution_context, node_id, node_type, error_msg, e, node_start_time)
        
        # Update final progress
        execution_context['progress'] = 100
        execution_time = time.time() - execution_context['start_time']
        add_debug_log(execution_context, 'info', None, f"Workflow execution completed in {execution_time:.3f} seconds")
        
        # Return execution results
        return format_execution_results(execution_context)
        
    except Exception as e:
        # Catch any unexpected exceptions at the top level
        error_msg = f"Unexpected error during workflow execution: {str(e)}"
        add_debug_log(execution_context, 'error', None, error_msg)
        add_debug_log(execution_context, 'error', None, f"Traceback: {traceback.format_exc()}")
        
        execution_context['errors'].append({
            'message': error_msg,
            'traceback': traceback.format_exc(),
            'timestamp': datetime.now().isoformat()
        })
        
        return format_execution_results(execution_context)
