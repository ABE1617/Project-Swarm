import importlib
import logging
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
    logger.info("Starting workflow execution")
    
    # Build dependency graph and get nodes
    graph, nodes = build_dependency_graph(workflow_data)
    
    # Get execution order
    try:
        execution_order = topological_sort(graph)
        logger.info(f"Execution order: {execution_order}")
    except ValueError as e:
        logger.error(f"Error in workflow topology: {str(e)}")
        raise
    
    # Execute each node in order
    context = {}
    results = {}
    
    for node_id in execution_order:
        node = nodes.get(node_id)
        if not node:
            logger.warning(f"Node {node_id} referenced in connections but not defined - skipping")
            continue
        
        node_type = node.get('type')
        node_config = node.get('config', {})
        
        try:
            # Dynamically import the node module
            module_name = f"control_nodes.{node_type}"
            module = importlib.import_module(module_name)
            
            # Process templates in node config (e.g., {{context.node1.result}})
            processed_config = process_config_templates(node_config, context)
            
            # Call the module's run function
            logger.info(f"Executing node {node_id} of type {node_type}")
            node_result = module.run(processed_config, context)
            
            # Store result in context
            context[node_id] = node_result
            results[node_id] = {
                'id': node_id,
                'type': node_type,
                'status': 'success',
                'result': node_result
            }
            
            logger.info(f"Node {node_id} executed successfully")
        
        except ImportError:
            error_msg = f"Node type '{node_type}' not found"
            logger.error(error_msg)
            results[node_id] = {
                'id': node_id,
                'type': node_type,
                'status': 'error',
                'error': error_msg
            }
        
        except Exception as e:
            error_msg = f"Error executing node {node_id}: {str(e)}"
            logger.error(error_msg)
            results[node_id] = {
                'id': node_id,
                'type': node_type,
                'status': 'error',
                'error': error_msg
            }
    
    logger.info("Workflow execution completed")
    return {
        'nodes': results,
        'context': context
    }

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
