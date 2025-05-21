document.addEventListener('DOMContentLoaded', function() {
    // Initialize jsPlumb with refined styling
    const jsPlumbInstance = jsPlumb.getInstance({
        Endpoint: ["Dot", { radius: 5 }],
        Connector: ["Bezier", { curviness: 60 }],
        PaintStyle: { 
            stroke: "rgba(83, 82, 237, 0.8)", 
            strokeWidth: 2 
        },
        HoverPaintStyle: { 
            stroke: "#2ed573", 
            strokeWidth: 3 
        },
        ConnectionOverlays: [
            ["Arrow", { 
                location: 1, 
                width: 10, 
                length: 10, 
                foldback: 0.8 
            }]
        ],
        Container: "workflow-canvas"
    });
    
    // GLOBAL STATE
    let nodes = {};
    let connections = [];
    let selectedNodeId = null;
    let currentWorkflowId = null;
    let currentWorkflowName = "Untitled Workflow";
    let nodeTypeDefinitions = {};
    
    // DOM ELEMENTS
    const canvas = document.getElementById('workflow-canvas');
    const configPanel = document.querySelector('.config-panel');
    const selectNodeMsg = document.querySelector('.select-node-msg');
    const nodeConfigForm = document.querySelector('.node-config');
    const closeConfigBtn = document.getElementById('close-config');
    const applyConfigBtn = document.getElementById('apply-config');
    const deleteNodeBtn = document.getElementById('delete-node');
    const workflowNameInput = document.getElementById('workflow-name');
    const saveWorkflowBtn = document.getElementById('save-workflow');
    const loadWorkflowBtn = document.getElementById('load-workflow');
    const newWorkflowBtn = document.getElementById('new-workflow');
    const executeWorkflowBtn = document.getElementById('execute-workflow');
    const importWorkflowBtn = document.getElementById('import-workflow');
    const exportWorkflowBtn = document.getElementById('export-workflow');
    const workflowListModal = new bootstrap.Modal(document.getElementById('workflow-list-modal'));
    const workflowResultModal = new bootstrap.Modal(document.getElementById('workflow-result-modal'));
    
    // ZOOM CONTROLS
    const zoomInButton = document.getElementById('zoom-in');
    const zoomOutButton = document.getElementById('zoom-out');
    const resetZoomButton = document.getElementById('reset-zoom');
    const zoomFitButton = document.getElementById('zoom-fit');
    const zoomLevelDisplay = document.getElementById('zoom-level-display');
    let zoomLevel = 1;
    
    // INITIALIZATION
    
    // Fetch node types from server
    fetchNodeTypes().then(types => {
        nodeTypeDefinitions = types;
        initDragAndDrop();
    });
    
    // Make the canvas droppable
    function initDragAndDrop() {
        // Make node items draggable
        const nodeItems = document.querySelectorAll('.node-item');
        nodeItems.forEach(nodeItem => {
            nodeItem.setAttribute('draggable', true);
            
            nodeItem.addEventListener('dragstart', function(e) {
                e.dataTransfer.setData('nodeType', this.getAttribute('data-node-type'));
            });
        });
        
        // Make canvas a drop target
        canvas.addEventListener('dragover', function(e) {
            e.preventDefault();
        });
        
        canvas.addEventListener('drop', function(e) {
            e.preventDefault();
            
            const nodeType = e.dataTransfer.getData('nodeType');
            if (nodeType) {
                // Get drop position relative to canvas
                const rect = canvas.getBoundingClientRect();
                const x = e.clientX - rect.left - 90; // Half node width
                const y = e.clientY - rect.top - 30;  // Half node height
                
                // Create node at drop position
                createNode(nodeType, x, y);
            }
        });
    }
    
    // Setup event handlers
    function setupEventHandlers() {
        // Close config panel
        closeConfigBtn.addEventListener('click', function() {
            hideConfigPanel();
        });
        
        // Apply node configuration
        applyConfigBtn.addEventListener('click', function() {
            applyNodeConfig();
        });
        
        // Delete selected node
        deleteNodeBtn.addEventListener('click', function() {
            deleteSelectedNode();
        });
        
        // Save workflow
        saveWorkflowBtn.addEventListener('click', function() {
            saveWorkflow();
        });
        
        // Load workflow
        loadWorkflowBtn.addEventListener('click', function() {
            fetchWorkflowList();
        });
        
        // New workflow
        newWorkflowBtn.addEventListener('click', function() {
            clearWorkflow();
        });
        
        // Execute workflow
        executeWorkflowBtn.addEventListener('click', function() {
            executeWorkflow();
        });
        
        // Update workflow name when input changes
        workflowNameInput.addEventListener('change', function() {
            currentWorkflowName = this.value || "Untitled Workflow";
        });
        
        // Import workflow
        importWorkflowBtn.addEventListener('click', function() {
            // Create a file input
            const fileInput = document.createElement('input');
            fileInput.type = 'file';
            fileInput.accept = '.json';
            
            fileInput.addEventListener('change', function(e) {
                const file = e.target.files[0];
                if (file) {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        try {
                            const workflowData = JSON.parse(e.target.result);
                            loadWorkflowData(workflowData);
                            currentWorkflowName = file.name.replace(/\.json$/, '') || "Imported Workflow";
                            workflowNameInput.value = currentWorkflowName;
                        } catch (error) {
                            alert('Invalid workflow file format');
                            console.error('Error parsing workflow file:', error);
                        }
                    };
                    reader.readAsText(file);
                }
            });
            
            fileInput.click();
        });
        
        // Export workflow
        exportWorkflowBtn.addEventListener('click', function() {
            const workflowData = serializeWorkflow();
            const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(workflowData, null, 2));
            const downloadAnchorNode = document.createElement('a');
            downloadAnchorNode.setAttribute("href", dataStr);
            downloadAnchorNode.setAttribute("download", `${currentWorkflowName}.json`);
            document.body.appendChild(downloadAnchorNode);
            downloadAnchorNode.click();
            downloadAnchorNode.remove();
        });
        
        // Add node search functionality
        const nodeSearch = document.getElementById('node-search');
        nodeSearch.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const nodeItems = document.querySelectorAll('.node-item');
            
            nodeItems.forEach(item => {
                const nodeLabel = item.querySelector('.node-label').textContent.toLowerCase();
                if (nodeLabel.includes(searchTerm)) {
                    item.style.display = '';
                } else {
                    item.style.display = 'none';
                }
            });
        });
        
        // Zoom controls
        zoomInButton.addEventListener('click', function() {
            console.log('Zoom In clicked'); // Debug log
            zoomLevel += 0.1; // Increase zoom level
            updateZoom();
        });
        
        zoomOutButton.addEventListener('click', function() {
            console.log('Zoom Out clicked'); // Debug log
            zoomLevel -= 0.1; // Decrease zoom level
            updateZoom();
        });
        
        resetZoomButton.addEventListener('click', function() {
            zoomLevel = 1; // Reset zoom level to 100%
            updateZoom();
        });
        
        zoomFitButton.addEventListener('click', function() {
            zoomLevel = 1; // Reset zoom level to 100%
            updateZoom();
        });
    }
    
    // NODE OPERATIONS
    
    // Create a new node with refined styling
    function createNode(nodeType, x, y) {
        // Generate unique node ID
        const nodeId = nodeType + '_' + Date.now();
        
        // Get node type definition
        const nodeTypeDef = nodeTypeDefinitions[nodeType];
        if (!nodeTypeDef) {
            console.error(`Node type ${nodeType} not found`);
            return;
        }
        
        // Create node DOM element
        const nodeEl = document.createElement('div');
        nodeEl.id = nodeId;
        nodeEl.className = 'workflow-node';
        nodeEl.dataset.nodeType = nodeType; // Store node type in dataset
        nodeEl.style.left = `${x}px`;
        nodeEl.style.top = `${y}px`;
        
        // Node header
        const nodeHeader = document.createElement('div');
        nodeHeader.className = 'node-header';
        
        const nodeIcon = document.createElement('div');
        nodeIcon.className = 'node-icon';
        nodeIcon.style.backgroundColor = nodeTypeDef.color;
        nodeIcon.innerHTML = `<i class="fas ${nodeTypeDef.icon}"></i>`;
        
        const nodeName = document.createElement('div');
        nodeName.className = 'node-name';
        nodeName.textContent = nodeTypeDef.name;
        
        // Add execution indicator dot
        const statusIndicator = document.createElement('div');
        statusIndicator.className = 'node-status';
        statusIndicator.style.display = 'none'; // Hidden by default
        
        nodeHeader.appendChild(nodeIcon);
        nodeHeader.appendChild(nodeName);
        nodeHeader.appendChild(statusIndicator);
        
        // Node ports
        const nodePorts = document.createElement('div');
        nodePorts.className = 'node-ports';
        
        // Input ports - don't create for manual_trigger
        if (nodeType !== 'manual_trigger' && nodeTypeDef.inputs && nodeTypeDef.inputs.length > 0) {
            const inputPort = document.createElement('div');
            inputPort.className = 'input-port';
            
            const inputHandle = document.createElement('div');
            inputHandle.className = 'port-handle input-handle';
            inputHandle.setAttribute('data-port', 'input');
            
            const inputLabel = document.createElement('div');
            inputLabel.className = 'port-label';
            inputLabel.textContent = 'Input';
            
            inputPort.appendChild(inputHandle);
            inputPort.appendChild(inputLabel);
            nodePorts.appendChild(inputPort);
        }
        
        // Special handling for If node - create two distinct output ports
        if (nodeType === 'if_condition') {
            // True output
            const trueOutputPort = document.createElement('div');
            trueOutputPort.className = 'output-port true-port';
            
            const trueOutputHandle = document.createElement('div');
            trueOutputHandle.className = 'port-handle output-handle true-handle';
            trueOutputHandle.setAttribute('data-port', 'true');
            
            const trueOutputLabel = document.createElement('div');
            trueOutputLabel.className = 'port-label';
            trueOutputLabel.textContent = 'True';
            
            trueOutputPort.appendChild(trueOutputLabel);
            trueOutputPort.appendChild(trueOutputHandle);
            nodePorts.appendChild(trueOutputPort);
            
            // False output
            const falseOutputPort = document.createElement('div');
            falseOutputPort.className = 'output-port false-port';
            
            const falseOutputHandle = document.createElement('div');
            falseOutputHandle.className = 'port-handle output-handle false-handle';
            falseOutputHandle.setAttribute('data-port', 'false');
            
            const falseOutputLabel = document.createElement('div');
            falseOutputLabel.className = 'port-label';
            falseOutputLabel.textContent = 'False';
            
            falseOutputPort.appendChild(falseOutputLabel);
            falseOutputPort.appendChild(falseOutputHandle);
            nodePorts.appendChild(falseOutputPort);
        } 
        // Regular output ports for other nodes
        else if (nodeTypeDef.outputs && nodeTypeDef.outputs.length > 0) {
            const outputPort = document.createElement('div');
            outputPort.className = 'output-port';
            
            const outputHandle = document.createElement('div');
            outputHandle.className = 'port-handle output-handle';
            outputHandle.setAttribute('data-port', 'output');
            
            const outputLabel = document.createElement('div');
            outputLabel.className = 'port-label';
            outputLabel.textContent = 'Output';
            
            outputPort.appendChild(outputLabel);
            outputPort.appendChild(outputHandle);
            nodePorts.appendChild(outputPort);
        }
        
        // Node content - special handling for certain nodes
        const nodeContent = document.createElement('div');
        nodeContent.className = 'node-content';
        
        // Special handling for Manual Trigger node
        if (nodeType === 'manual_trigger') {
            const startButton = document.createElement('button');
            startButton.className = 'btn btn-success btn-sm start-workflow-btn';
            startButton.innerHTML = '<i class="fas fa-play"></i> Start';
            startButton.title = 'Execute workflow starting from here';
            startButton.addEventListener('click', (e) => {
                e.stopPropagation(); // Don't trigger node selection
                executeWorkflow();
            });
            
            nodeContent.appendChild(startButton);
        }
        
        // Quick action buttons (only visible when node is selected)
        const quickActions = document.createElement('div');
        quickActions.className = 'node-quick-actions';
        quickActions.style.display = 'none'; // Hidden by default
        
        const editBtn = document.createElement('button');
        editBtn.className = 'btn btn-sm btn-primary quick-edit-btn';
        editBtn.innerHTML = '<i class="fas fa-cog"></i>';
        editBtn.title = 'Edit Node';
        editBtn.addEventListener('click', (e) => {
            e.stopPropagation(); // Don't trigger node selection
            showConfigPanel(nodeId);
        });
        
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'btn btn-sm btn-danger quick-delete-btn';
        deleteBtn.innerHTML = '<i class="fas fa-trash"></i>';
        deleteBtn.title = 'Delete Node';
        deleteBtn.addEventListener('click', (e) => {
            e.stopPropagation(); // Don't trigger node selection
            if (confirm('Are you sure you want to delete this node?')) {
                deleteSelectedNode();
            }
        });
        
        quickActions.appendChild(editBtn);
        quickActions.appendChild(deleteBtn);
        
        // Assemble node
        nodeEl.appendChild(nodeHeader);
        nodeEl.appendChild(nodePorts);
        nodeEl.appendChild(nodeContent);
        nodeEl.appendChild(quickActions);
        canvas.appendChild(nodeEl);
        
        // Add node to state
        nodes[nodeId] = {
            id: nodeId,
            type: nodeType,
            position: { x, y },
            config: {}
        };
        
        // Make node draggable with improved configuration
        jsPlumbInstance.draggable(nodeId, {
            grid: [10, 10],
            containment: true, // Contain within canvas but allow scrolling
            stop: function(event) {
                // Update node position in state
                nodes[nodeId].position.x = parseInt(event.pos[0]);
                nodes[nodeId].position.y = parseInt(event.pos[1]);
            }
        });
        
        // Make end points for Regular nodes
        if (nodeType !== 'if_condition') {
            // Special case for manual_trigger - it should not have inputs
            if (nodeType === 'manual_trigger') {
                // Only create output endpoints
                if (nodeTypeDef.outputs && nodeTypeDef.outputs.length > 0) {
                    jsPlumbInstance.makeSource(nodeEl.querySelector('.output-handle'), {
                        anchor: 'Right',
                        maxConnections: -1
                    });
                }
            } else {
                // For all other regular nodes
                if (nodeTypeDef.inputs && nodeTypeDef.inputs.length > 0) {
                    jsPlumbInstance.makeTarget(nodeEl.querySelector('.input-handle'), {
                        anchor: 'Left',
                        maxConnections: -1
                    });
                }
                
                if (nodeTypeDef.outputs && nodeTypeDef.outputs.length > 0) {
                    jsPlumbInstance.makeSource(nodeEl.querySelector('.output-handle'), {
                        anchor: 'Right',
                        maxConnections: -1
                    });
                }
            }
        } 
        // Special endpoint configuration for If node
        else {
            // Make the input handle a target
            jsPlumbInstance.makeTarget(nodeEl.querySelector('.input-handle'), {
                anchor: 'Left',
                maxConnections: -1
            });
            
            // Make the true and false handles sources
            jsPlumbInstance.makeSource(nodeEl.querySelector('.true-handle'), {
                anchor: 'Right',
                maxConnections: -1
            });
            
            jsPlumbInstance.makeSource(nodeEl.querySelector('.false-handle'), {
                anchor: 'Right',
                maxConnections: -1
            });
        }
        
        // Setup connection listeners
        jsPlumbInstance.bind('connection', function(info) {
            // Add connection to state
            connections.push({
                source: info.sourceId,
                target: info.targetId,
                sourcePort: info.sourceId === nodeId ? info.source.dataset.port : undefined,
                targetPort: info.targetId === nodeId ? info.target.dataset.port : undefined
            });
            
            // Remove guide when first connection is made
            document.querySelector('.canvas-guide')?.remove();
        });
        
        jsPlumbInstance.bind('connectionDetached', function(info) {
            // Remove connection from state
            connections = connections.filter(conn => 
                !(conn.source === info.sourceId && conn.target === info.targetId));
        });
        
        // Make node selectable
        nodeEl.addEventListener('click', function(e) {
            e.stopPropagation();
            selectNode(nodeId);
        });
        
        // Remove guide on first node creation
        document.querySelector('.canvas-guide')?.remove();
        
        // Select the new node to configure it
        selectNode(nodeId);
        
        // Add subtle entrance animation
        nodeEl.style.opacity = '0';
        nodeEl.style.transform = 'scale(0.95)';
        setTimeout(() => {
            nodeEl.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
            nodeEl.style.opacity = '1';
            nodeEl.style.transform = 'scale(1)';
        }, 10);
        
        return nodeId;
    }
    
    // Select a node
    function selectNode(nodeId) {
        // Hide quick actions on previously selected node
        if (selectedNodeId) {
            const prevNode = document.getElementById(selectedNodeId);
            if (prevNode) {
                prevNode.classList.remove('node-selected');
                const prevQuickActions = prevNode.querySelector('.node-quick-actions');
                if (prevQuickActions) {
                    prevQuickActions.style.display = 'none';
                }
            }
        }
        
        // Update selected node
        selectedNodeId = nodeId;
        
        // Highlight selected node and show quick actions
        const nodeEl = document.getElementById(nodeId);
        if (nodeEl) {
            nodeEl.classList.add('node-selected');
            
            // Show quick action buttons
            const quickActions = nodeEl.querySelector('.node-quick-actions');
            if (quickActions) {
                quickActions.style.display = 'flex';
            }
        }
        
        // Show configuration panel
        showConfigPanel(nodeId);
    }
    
    // Delete the selected node
    function deleteSelectedNode() {
        if (!selectedNodeId) return;
        
        // Remove connections
        jsPlumbInstance.remove(selectedNodeId);
        
        // Remove node from state
        delete nodes[selectedNodeId];
        
        // Update connections state
        connections = connections.filter(conn => 
            conn.source !== selectedNodeId && conn.target !== selectedNodeId);
        
        // Hide config panel
        hideConfigPanel();
        
        // Clear selection
        selectedNodeId = null;
    }
    
    // CONFIGURATION PANEL
    
    // Show configuration panel for a node
    function showConfigPanel(nodeId) {
        const node = nodes[nodeId];
        if (!node) return;
        
        const nodeTypeDef = nodeTypeDefinitions[node.type];
        if (!nodeTypeDef) return;
        
        // Hide the select node message
        selectNodeMsg.style.display = 'none';
        
        // Show the node config form
        nodeConfigForm.style.display = 'block';
        
        // Update node icon and title
        const nodeIcon = nodeConfigForm.querySelector('.node-icon');
        nodeIcon.style.backgroundColor = nodeTypeDef.color;
        nodeIcon.innerHTML = `<i class="fas ${nodeTypeDef.icon}"></i>`;
        
        const nodeTitle = nodeConfigForm.querySelector('.node-title');
        nodeTitle.textContent = nodeTypeDef.name;
        
        // Generate form fields based on config schema
        const configFormEl = nodeConfigForm.querySelector('.node-config-form');
        configFormEl.innerHTML = '';
        
        if (nodeTypeDef.configSchema) {
            for (const [key, schema] of Object.entries(nodeTypeDef.configSchema)) {
                // Check if field should be shown
                if (schema.showIf) {
                    // Skip field if condition not met
                    let shouldShow = true;
                    for (const [condKey, condValue] of Object.entries(schema.showIf)) {
                        if (node.config[condKey] !== condValue) {
                            shouldShow = false;
                            break;
                        }
                    }
                    
                    if (!shouldShow) {
                        continue;
                    }
                }
                
                const formField = createFormField(key, schema);
                configFormEl.appendChild(formField);
                
                // Set current value if exists
                const input = formField.querySelector(`#${key}`);
                if (input && node.config[key] !== undefined) {
                    if (input.type === 'checkbox') {
                        input.checked = node.config[key];
                    } else if (schema.type === 'object' || schema.type === 'array') {
                        input.value = JSON.stringify(node.config[key], null, 2);
                    } else {
                        input.value = node.config[key];
                    }
                }
                
                // Add event listeners for conditional fields
                if (schema.showIf) {
                    input.addEventListener('change', function() {
                        // Refresh the form to update conditional fields
                        showConfigPanel(nodeId);
                    });
                }
                
                // Add auto-save functionality
                if (input) {
                    const eventType = input.type === 'checkbox' ? 'change' : 'input';
                    input.addEventListener(eventType, () => {
                        // Get the value based on input type
                        let value;
                        if (input.type === 'checkbox') {
                            value = input.checked;
                        } else if (schema.type === 'object' || schema.type === 'array') {
                            try {
                                value = JSON.parse(input.value || '{}');
                            } catch (e) {
                                console.error(`JSON parse error in ${key}:`, e);
                                return;
                            }
                        } else {
                            value = input.value;
                        }
                        
                        // Update node config
                        if (!node.config) node.config = {};
                        node.config[key] = value;
                        
                        // Visual feedback for auto-save
                        const saveBtn = document.getElementById('apply-config');
                        saveBtn.innerHTML = '<i class="fas fa-check"></i> Saved';
                        saveBtn.classList.remove('btn-primary');
                        saveBtn.classList.add('btn-success');
                        
                        // Reset button after delay
                        setTimeout(() => {
                            saveBtn.innerHTML = '<i class="fas fa-save"></i> Apply';
                            saveBtn.classList.remove('btn-success');
                            saveBtn.classList.add('btn-primary');
                        }, 1000);
                    });
                }
            }
        }
    }
    
    // Hide configuration panel
    function hideConfigPanel() {
        // Show the select node message
        selectNodeMsg.style.display = 'flex';
        
        // Hide the node config form
        nodeConfigForm.style.display = 'none';
        
        // Clear selection
        if (selectedNodeId) {
            document.getElementById(selectedNodeId)?.classList.remove('node-selected');
            selectedNodeId = null;
        }
    }
    
    // Apply node configuration
    function applyNodeConfig() {
        if (!selectedNodeId) return;
        
        const node = nodes[selectedNodeId];
        if (!node) return;
        
        const nodeTypeDef = nodeTypeDefinitions[node.type];
        if (!nodeTypeDef) return;
        
        // Collect form values
        const config = {};
        
        if (nodeTypeDef.configSchema) {
            for (const [key, schema] of Object.entries(nodeTypeDef.configSchema)) {
                const input = document.getElementById(key);
                if (!input) continue;
                
                if (input.type === 'checkbox') {
                    config[key] = input.checked;
                } else if (schema.type === 'object' || schema.type === 'array') {
                    try {
                        config[key] = JSON.parse(input.value || '{}');
                    } catch (e) {
                        alert(`Invalid JSON for field ${schema.title || key}`);
                        console.error(`JSON parse error in ${key}:`, e);
                        return;
                    }
                } else {
                    config[key] = input.value;
                }
            }
        }
        
        // Update node config
        node.config = config;
        
        // Show success message
        alert('Node configuration applied');
    }
    
    // WORKFLOW OPERATIONS
    
    // Serialize workflow to JSON
    function serializeWorkflow(options = {}) {
        // Get all connections from jsPlumb
        const jsPlumbConnections = jsPlumbInstance.getConnections();
        
        // Map connections to the correct format
        const serializedConnections = jsPlumbConnections.map(conn => {
            // Get the parent node elements that contain these endpoints
            const sourceNodeEl = conn.source.closest('.workflow-node');
            const targetNodeEl = conn.target.closest('.workflow-node');
            
            // Get the node IDs from the elements
            const sourceNodeId = sourceNodeEl.id;
            const targetNodeId = targetNodeEl.id;
            
            // Get port information if available
            const sourcePort = conn.source.getAttribute('data-port') || 'output';
            const targetPort = conn.target.getAttribute('data-port') || 'input';
            
            return {
                source: sourceNodeId,
                target: targetNodeId,
                sourcePort: sourcePort,
                targetPort: targetPort
            };
        });
        
        // If skipFilter is set, return all nodes/connections (for validation)
        if (options.skipFilter) {
            return {
                nodes: Object.values(nodes),
                connections: serializedConnections,
                variables: {}
            };
        }
        
        // Otherwise, filter to only include nodes in execution order
        let executionOrder = [];
        if (typeof validateAndPrepareExecution === 'function') {
            const validation = validateAndPrepareExecution();
            if (validation && validation.executionOrder) {
                executionOrder = validation.executionOrder;
            }
        }
        const nodeSet = new Set(executionOrder);
        const filteredNodes = Object.values(nodes).filter(n => nodeSet.has(n.id));
        const filteredConnections = serializedConnections.filter(conn => nodeSet.has(conn.source) && nodeSet.has(conn.target));
        return {
            nodes: filteredNodes,
            connections: filteredConnections,
            variables: {}
        };
    }
    
    // Clear current workflow
    function clearWorkflow() {
        // Clear jsPlumb instance
        jsPlumbInstance.reset();
        
        // Clear node elements
        canvas.querySelectorAll('.workflow-node').forEach(el => el.remove());
        
        // Reset state
        nodes = {};
        connections = [];
        selectedNodeId = null;
        currentWorkflowId = null;
        currentWorkflowName = "Untitled Workflow";
        workflowNameInput.value = currentWorkflowName;
        
        // Hide config panel
        hideConfigPanel();
        
        // Re-add guide
        const canvasGuide = document.createElement('div');
        canvasGuide.className = 'canvas-guide';
        canvasGuide.innerHTML = `
            <div class="guide-content">
                <i class="fas fa-arrow-left fa-2x mb-3"></i>
                <h4>Build Your Workflow</h4>
                <p>Drag nodes from the sidebar and drop them here to start building your workflow.</p>
            </div>
        `;
        canvas.appendChild(canvasGuide);
    }
    
    // Save workflow to server
    function saveWorkflow() {
        const workflow = serializeWorkflow();
        
        fetch('/api/save-workflow', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                name: currentWorkflowName,
                workflow: workflow
            }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Workflow saved successfully');
                currentWorkflowId = data.id;
            } else {
                alert('Error saving workflow: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error saving workflow:', error);
            alert('Error saving workflow');
        });
    }
    
    // Fetch list of saved workflows
    function fetchWorkflowList() {
        fetch('/api/workflows')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const workflowList = document.getElementById('workflow-list');
                    const noWorkflowsMsg = document.getElementById('no-workflows');
                    
                    // Clear existing list
                    workflowList.innerHTML = '';
                    
                    if (data.workflows.length === 0) {
                        noWorkflowsMsg.style.display = 'block';
                    } else {
                        noWorkflowsMsg.style.display = 'none';
                        
                        // Add workflows to list
                        data.workflows.forEach(workflow => {
                            const workflowItem = document.createElement('a');
                            workflowItem.href = '#';
                            workflowItem.className = 'list-group-item list-group-item-action';
                            workflowItem.innerHTML = `
                                <div class="d-flex w-100 justify-content-between">
                                    <h5 class="mb-1">${workflow.name}</h5>
                                    <small>${new Date(workflow.updated_at).toLocaleString()}</small>
                                </div>
                                <div class="d-flex justify-content-between">
                                    <small>ID: ${workflow.id}</small>
                                    <div>
                                        <button class="btn btn-sm btn-outline-danger delete-workflow" data-id="${workflow.id}">
                                            <i class="fas fa-trash-alt"></i>
                                        </button>
                                    </div>
                                </div>
                            `;
                            
                            workflowItem.addEventListener('click', function(e) {
                                if (!e.target.closest('.delete-workflow')) {
                                    // Load workflow
                                    loadWorkflow(workflow.id);
                                    workflowListModal.hide();
                                }
                            });
                            
                            workflowList.appendChild(workflowItem);
                        });
                        
                        // Add delete workflow button handlers
                        document.querySelectorAll('.delete-workflow').forEach(btn => {
                            btn.addEventListener('click', function(e) {
                                e.preventDefault();
                                e.stopPropagation();
                                
                                const workflowId = this.getAttribute('data-id');
                                if (confirm('Are you sure you want to delete this workflow?')) {
                                    deleteWorkflow(workflowId);
                                }
                            });
                        });
                    }
                    
                    workflowListModal.show();
                } else {
                    alert('Error fetching workflows: ' + data.error);
                }
            })
            .catch(error => {
                console.error('Error fetching workflows:', error);
                alert('Error fetching workflows');
            });
    }
    
    // Load workflow by ID
    function loadWorkflow(workflowId) {
        fetch(`/api/workflows/${workflowId}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    loadWorkflowData(data.workflow.data);
                    currentWorkflowId = workflowId;
                    currentWorkflowName = data.workflow.name;
                    workflowNameInput.value = currentWorkflowName;
                } else {
                    alert('Error loading workflow: ' + data.error);
                }
            })
            .catch(error => {
                console.error('Error loading workflow:', error);
                alert('Error loading workflow');
            });
    }
    
    // Delete workflow by ID
    function deleteWorkflow(workflowId) {
        fetch(`/api/workflows/${workflowId}`, {
            method: 'DELETE'
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('Workflow deleted successfully');
                    fetchWorkflowList(); // Refresh the list
                } else {
                    alert('Error deleting workflow: ' + data.error);
                }
            })
            .catch(error => {
                console.error('Error deleting workflow:', error);
                alert('Error deleting workflow');
            });
    }
    
    // Load workflow data into the editor
    function loadWorkflowData(workflowData) {
        // Clear existing workflow
        clearWorkflow();
        
        // Create nodes first
        const nodeMap = {};
        if (workflowData.nodes && Array.isArray(workflowData.nodes)) {
            workflowData.nodes.forEach((node, index) => {
                // Position nodes in a grid layout if no position
                const x = 100 + (index % 3) * 250;
                const y = 100 + Math.floor(index / 3) * 150;
                
                const nodeId = createNode(node.type, x, y);
                nodeMap[node.id] = nodeId;
                
                // Set node configuration
                nodes[nodeId].config = node.config || {};
            });
        }
        
        // Create connections
        if (workflowData.connections && Array.isArray(workflowData.connections)) {
            // We need to wait for jsPlumb to be ready
            setTimeout(() => {
                workflowData.connections.forEach(connection => {
                    const sourceId = nodeMap[connection.source];
                    const targetId = nodeMap[connection.target];
                    
                    if (sourceId && targetId) {
                        jsPlumbInstance.connect({
                            source: document.querySelector(`#${sourceId} .output-handle`),
                            target: document.querySelector(`#${targetId} .input-handle`),
                            type: "basic"
                        });
                    }
                });
            }, 100);
        }
    }
    
    // Helper function to show workflow errors
    function showWorkflowError(message) {
        console.error("Workflow error:", message);
        
        // Create error message
        const errorToast = document.createElement('div');
        errorToast.className = 'alert alert-danger';
        errorToast.innerHTML = `<i class="fas fa-exclamation-circle"></i> Error: ${message}`;
        errorToast.style.position = 'fixed';
        errorToast.style.top = '20px';
        errorToast.style.left = '50%';
        errorToast.style.transform = 'translateX(-50%)';
        errorToast.style.zIndex = '9999';
        errorToast.style.padding = '10px 20px';
        errorToast.style.boxShadow = '0 4px 8px rgba(0,0,0,0.1)';
        
        document.body.appendChild(errorToast);
        
        // Remove after 5 seconds
        setTimeout(() => {
            errorToast.style.opacity = '0';
            errorToast.style.transition = 'opacity 0.5s ease';
            setTimeout(() => errorToast.remove(), 500);
        }, 5000);
    }
    
    // --- NEW: Validation and Execution Preparation ---
    function validateAndPrepareExecution() {
        // Clear previous error states
        clearNodeErrorStates();
        clearLonelyNodeWarnings();

        // 1. Find all manual_trigger nodes
        const triggerNodes = Object.values(nodes).filter(n => n.type === 'manual_trigger');
        if (triggerNodes.length === 0) {
            showWorkflowError('Workflow must have at least one manual trigger node to execute.');
            return { valid: false };
        }

        // 2. Check each manual_trigger node is connected to at least one other node
        const workflow = serializeWorkflow({ skipFilter: true }); // get all nodes/connections
        const { nodes: nodeList, connections: connList } = workflow;
        const nodeIdSet = new Set(nodeList.map(n => n.id));
        let triggerConnected = false;
        for (const trigger of triggerNodes) {
            if (connList.some(conn => conn.source === trigger.id)) {
                triggerConnected = true;
                break;
            }
        }
        if (!triggerConnected) {
            showWorkflowError('Manual trigger node must be connected to at least one other node.');
            // Mark all manual triggers as error
            triggerNodes.forEach(trigger => markNodeError(trigger.id, 'Manual trigger not connected'));
            return { valid: false };
        }

        // 3. Build execution order using FIFO queue (BFS), respecting connection creation order
        // Build adjacency list (outgoing edges)
        const adj = {};
        connList.forEach(conn => {
            if (!adj[conn.source]) adj[conn.source] = [];
            adj[conn.source].push({ target: conn.target, sourcePort: conn.sourcePort, targetPort: conn.targetPort });
        });
        // Track visited nodes to avoid cycles
        const visited = new Set();
        const executionOrder = [];
        const queue = [];
        // Enqueue all manual triggers in order
        triggerNodes.forEach(trigger => {
            queue.push(trigger.id);
            visited.add(trigger.id);
        });
        while (queue.length > 0) {
            const nodeId = queue.shift();
            executionOrder.push(nodeId);
            if (adj[nodeId]) {
                for (const edge of adj[nodeId]) {
                    if (!visited.has(edge.target)) {
                        queue.push(edge.target);
                        visited.add(edge.target);
                    }
                }
            }
        }
        // --- Lonely node detection ---
        const lonelyNodes = Object.keys(nodes).filter(nodeId => !executionOrder.includes(nodeId));
        lonelyNodes.forEach(nodeId => markLonelyNodeWarning(nodeId));
        if (lonelyNodes.length > 0) {
            showWorkflowError('Some nodes are not connected to the workflow and will not be executed. Please connect or remove them.');
            
        }
        // 4. Validate each node in execution order
        for (const nodeId of executionOrder) {
            const node = nodes[nodeId];
            const nodeTypeDef = nodeTypeDefinitions[node.type];
            if (!nodeTypeDef) continue;
            // Skip all validation for manual_trigger nodes
            if (node.type === 'manual_trigger') continue;
            // Field validation
            if (nodeTypeDef.configSchema) {
                for (const [key, schema] of Object.entries(nodeTypeDef.configSchema)) {
                    // Only check visible fields (respect showIf)
                    if (schema.showIf) {
                        let shouldShow = true;
                        for (const [condKey, condValue] of Object.entries(schema.showIf)) {
                            if (node.config[condKey] !== condValue) {
                                shouldShow = false;
                                break;
                            }
                        }
                        if (!shouldShow) continue;
                    }
                    // Required field check
                    if (schema.required && (node.config[key] === undefined || node.config[key] === null || node.config[key] === '')) {
                        markNodeError(nodeId, `Missing required field: ${schema.title || key}`);
                        showWorkflowError(`Node "${nodeTypeDef.name}" is missing required field: ${schema.title || key}`);
                        return { valid: false };
                    }
                    // Type check (basic)
                    if (schema.type === 'number' && isNaN(Number(node.config[key]))) {
                        markNodeError(nodeId, `Field ${schema.title || key} must be a number`);
                        showWorkflowError(`Node "${nodeTypeDef.name}" field ${schema.title || key} must be a number`);
                        return { valid: false };
                    }
                    if (schema.type === 'object' || schema.type === 'array') {
                        try {
                            if (typeof node.config[key] === 'string') {
                                JSON.parse(node.config[key]);
                            }
                        } catch (e) {
                            markNodeError(nodeId, `Invalid JSON in field: ${schema.title || key}`);
                            showWorkflowError(`Node "${nodeTypeDef.name}" has invalid JSON in field: ${schema.title || key}`);
                            return { valid: false };
                        }
                    }
                }
            }
            // Dependency validation: check all input nodes exist
            if (nodeTypeDef.inputs && nodeTypeDef.inputs.length > 0) {
                // For each input, check if there is at least one incoming connection
                const hasInput = connList.some(conn => conn.target === nodeId);
                if (!hasInput) {
                    markNodeError(nodeId, 'Missing input connection');
                    showWorkflowError(`Node "${nodeTypeDef.name}" is missing input connection.`);
                    return { valid: false };
                }
            }
        }
        // All checks passed
        return { valid: true, executionOrder };
    }

    // Helper to mark a node as error and show icon
    function markNodeError(nodeId, message) {
        const nodeEl = document.getElementById(nodeId);
        if (!nodeEl) return;
        nodeEl.classList.add('node-error');
        // Remove existing error badge if any
        nodeEl.querySelectorAll('.node-error-badge').forEach(b => b.remove());
        // Add error badge
        const errorBadge = document.createElement('div');
        errorBadge.className = 'node-error-badge';
        errorBadge.innerHTML = '<i class="fas fa-exclamation-triangle"></i>';
        errorBadge.title = message || 'Node validation error';
        nodeEl.appendChild(errorBadge);
    }

    // Helper to mark a node as lonely (yellow warning)
    function markLonelyNodeWarning(nodeId) {
        const nodeEl = document.getElementById(nodeId);
        if (!nodeEl) return;
        // Remove existing lonely badge if any
        nodeEl.querySelectorAll('.node-lonely-badge').forEach(b => b.remove());
        // Add lonely badge
        const lonelyBadge = document.createElement('div');
        lonelyBadge.className = 'node-lonely-badge';
        lonelyBadge.style.position = 'absolute';
        lonelyBadge.style.top = '-18px';
        lonelyBadge.style.left = '50%';
        lonelyBadge.style.transform = 'translateX(-50%)';
        lonelyBadge.style.background = '#ffe066';
        lonelyBadge.style.color = '#856404';
        lonelyBadge.style.borderRadius = '8px';
        lonelyBadge.style.padding = '2px 8px';
        lonelyBadge.style.fontSize = '0.8em';
        lonelyBadge.style.boxShadow = '0 2px 6px rgba(0,0,0,0.08)';
        lonelyBadge.innerHTML = '<i class="fas fa-exclamation-circle"></i> Not connected';
        nodeEl.appendChild(lonelyBadge);
    }

    // Helper to clear all lonely node warnings
    function clearLonelyNodeWarnings() {
        document.querySelectorAll('.node-lonely-badge').forEach(b => b.remove());
    }

    // --- REPLACE executeWorkflow ---
    function executeWorkflow() {
        // Clear any previous error states
        clearNodeErrorStates();
        // Validate and prepare execution order
        const validation = validateAndPrepareExecution();
        if (!validation.valid) {
            // Abort execution if validation failed
            return;
        }
        // If all checks pass, proceed as before
        const workflow = serializeWorkflow();
        // Show execution progress
        showExecutionProgress(0);
        // Clear debug logs
        clearDebugLogs();
        // Update UI
        executeWorkflowBtn.disabled = true;
        executeWorkflowBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Executing...';
        // Switch to debug tab
        document.getElementById('debug-tab').click();
        // Add initial log
        addDebugLogEntry({
            timestamp: new Date().toISOString(),
            level: 'info',
            node_id: null,
            message: 'Starting workflow execution...'
        });
        fetch('/api/run-workflow', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(workflow),
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // Hide progress bar
            hideExecutionProgress();
            // Re-enable button
            executeWorkflowBtn.disabled = false;
            executeWorkflowBtn.innerHTML = '<i class="fas fa-play me-1"></i> Execute';
            if (data.success) {
                // Show success message in debug log
                addDebugLogEntry({
                    timestamp: new Date().toISOString(),
                    level: 'success',
                    node_id: null,
                    message: `Workflow execution completed in ${data.results.execution_time.toFixed(2)} seconds`
                });
                // Update debug logs
                if (data.results.debug_logs && data.results.debug_logs.length > 0) {
                    populateDebugLogs(data.results.debug_logs);
                }
                // Highlight nodes with their status
                if (data.results.node_statuses) {
                    updateNodeStatuses(data.results.node_statuses);
                }
                // Display detailed results
                displayWorkflowResults(data.results);
                // If there are errors, ensure they're visible
                if (data.results.errors && data.results.errors.length > 0) {
                    data.results.errors.forEach(error => {
                        addDebugLogEntry({
                            timestamp: new Date().toISOString(),
                            level: 'error',
                            node_id: error.node_id || null,
                            message: `Error: ${error.message}`
                        });
                    });
                }
            } else {
                // Handle API error response
                const errorMessage = data.error || 'Unknown error executing workflow';
                console.error('Error executing workflow:', errorMessage);
                addDebugLogEntry({
                    timestamp: new Date().toISOString(),
                    level: 'error',
                    node_id: null,
                    message: `Error executing workflow: ${errorMessage}`
                });
                if (data.traceback) {
                    addDebugLogEntry({
                        timestamp: new Date().toISOString(),
                        level: 'error',
                        node_id: null,
                        message: `Traceback: ${data.traceback}`
                    });
                }
            }
        })
        .catch(error => {
            hideExecutionProgress();
            executeWorkflowBtn.disabled = false;
            executeWorkflowBtn.innerHTML = '<i class="fas fa-play me-1"></i> Execute';
            console.error('Error executing workflow:', error);
            addDebugLogEntry({
                timestamp: new Date().toISOString(),
                level: 'error',
                node_id: null,
                message: `Network error: ${error.message}`
            });
        });
    }
    
    // Debug panel utility functions
    function clearNodeErrorStates() {
        // Remove error indicators from all nodes
        document.querySelectorAll('.workflow-node').forEach(node => {
            node.classList.remove('node-error');
            const errorBadge = node.querySelector('.node-error-badge');
            if (errorBadge) {
                errorBadge.remove();
            }
            
            // Remove status indicators
            const statusIndicator = node.querySelector('.node-status');
            if (statusIndicator) {
                statusIndicator.remove();
            }
        });
    }
    
    function showExecutionProgress(percent) {
        const progressBar = document.getElementById('execution-progress-bar');
        if (!progressBar) return;
        
        const progressIndicator = progressBar.querySelector('.progress-bar');
        if (progressIndicator) {
            progressIndicator.style.width = `${percent}%`;
            progressIndicator.setAttribute('aria-valuenow', percent);
            progressIndicator.textContent = `${percent}%`;
        }
        
        progressBar.style.display = 'block';
    }
    
    function hideExecutionProgress() {
        const progressBar = document.getElementById('execution-progress-bar');
        if (progressBar) {
            progressBar.style.display = 'none';
        }
    }
    
    function updateNodeStatuses(nodeStatuses) {
        // Update visual status of each node
        Object.entries(nodeStatuses).forEach(([nodeId, status]) => {
            const nodeEl = document.getElementById(nodeId);
            if (!nodeEl) {
                console.warn(`Node element with ID ${nodeId} not found`);
                return;
            }
            
            // Remove any existing status indicators
            nodeEl.querySelectorAll('.node-status').forEach(el => el.remove());
            
            // Add status indicator
            const statusIndicator = document.createElement('div');
            statusIndicator.className = `node-status status-${status}`;
            statusIndicator.title = `Status: ${status}`;
            nodeEl.appendChild(statusIndicator);
            
            // Remove any existing error badges
            const existingBadge = nodeEl.querySelector('.node-error-badge');
            if (existingBadge) {
                existingBadge.remove();
            }
            
            // Add error badge if node failed
            if (status === 'error') {
                nodeEl.classList.add('node-error');
                
                const errorBadge = document.createElement('div');
                errorBadge.className = 'node-error-badge';
                errorBadge.innerHTML = '<i class="fas fa-exclamation-triangle"></i>';
                errorBadge.title = 'Node execution failed - click to view error details';
                
                // Add click handler to show error panel instead of just switching to debug tab
                errorBadge.addEventListener('click', (e) => {
                    e.stopPropagation(); // Don't select the node
                    
                    // Find error information for this node
                    const nodeResult = getNodeExecutionResult(nodeId);
                    if (nodeResult && nodeResult.error) {
                        // Show contextual error panel
                        showWorkflowError(nodeResult.error, nodeId);
                    } else {
                        // Fallback to debug tab if we can't find specific error info
                        document.getElementById('debug-tab').click();
                        
                        // Find and highlight the error log for this node
                        const logEntries = document.querySelectorAll('.debug-log-entry');
                        logEntries.forEach(entry => {
                            const nodeIdSpan = entry.querySelector('.debug-node-id');
                            if (nodeIdSpan && nodeIdSpan.textContent === nodeId && entry.classList.contains('log-error')) {
                                // Highlight this entry
                                entry.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                entry.classList.add('highlight-log');
                                
                                // Remove highlight after a delay
                                setTimeout(() => {
                                    entry.classList.remove('highlight-log');
                                }, 2000);
                            }
                        });
                    }
                });
                
                nodeEl.appendChild(errorBadge);
            } else if (status === 'success') {
                // If node was successful, remove error class
                nodeEl.classList.remove('node-error');
            }
        });
    }
    
    // Helper function to get node execution result
    function getNodeExecutionResult(nodeId) {
        // Check if we have results stored
        if (window.lastWorkflowResults && window.lastWorkflowResults.nodes && window.lastWorkflowResults.nodes[nodeId]) {
            return window.lastWorkflowResults.nodes[nodeId];
        }
        return null;
    }
    
    function clearDebugLogs() {
        const logContainer = document.getElementById('debug-log-container');
        if (logContainer) {
            logContainer.innerHTML = '';
        }
        
        // Show empty message
        const emptyMsg = document.querySelector('.debug-log-empty');
        if (emptyMsg) {
            emptyMsg.style.display = 'block';
        }
    }
    
    function populateDebugLogs(logs) {
        const logContainer = document.getElementById('debug-log-container');
        if (!logContainer) return;
        
        // Hide empty message
        const emptyMsg = document.querySelector('.debug-log-empty');
        if (emptyMsg) {
            emptyMsg.style.display = 'none';
        }
        
        // Clear existing logs
        logContainer.innerHTML = '';
        
        // Add each log entry
        logs.forEach(log => {
            const logEntry = document.createElement('div');
            logEntry.className = `debug-log-entry log-${log.level}`;
            
            const logTime = document.createElement('div');
            logTime.className = 'debug-log-time';
            
            // Format timestamp
            const timestamp = new Date(log.timestamp);
            logTime.textContent = timestamp.toLocaleTimeString();
            
            const logContent = document.createElement('div');
            logContent.className = 'debug-log-content';
            
            // Add node ID if present
            if (log.node_id) {
                const nodeSpan = document.createElement('span');
                nodeSpan.className = 'debug-node-id';
                nodeSpan.textContent = log.node_id;
                logContent.appendChild(nodeSpan);
            }
            
            // Add message
            const messageSpan = document.createElement('span');
            messageSpan.className = 'debug-message';
            messageSpan.textContent = log.message;
            logContent.appendChild(messageSpan);
            
            logEntry.appendChild(logTime);
            logEntry.appendChild(logContent);
            logContainer.appendChild(logEntry);
        });
        
        // Scroll to bottom
        logContainer.scrollTop = logContainer.scrollHeight;
    }
    
    // Add a single debug log entry
    function addDebugLogEntry(log) {
        const logContainer = document.getElementById('debug-log-container');
        if (!logContainer) return;
        
        // Hide empty message
        const emptyMsg = document.querySelector('.debug-log-empty');
        if (emptyMsg) {
            emptyMsg.style.display = 'none';
        }
        
        const logEntry = document.createElement('div');
        logEntry.className = `debug-log-entry log-${log.level}`;
        
        const logTime = document.createElement('div');
        logTime.className = 'debug-log-time';
        
        // Format timestamp
        const timestamp = new Date(log.timestamp);
        logTime.textContent = timestamp.toLocaleTimeString();
        
        const logContent = document.createElement('div');
        logContent.className = 'debug-log-content';
        
        // Add node ID if present
        if (log.node_id) {
            const nodeSpan = document.createElement('span');
            nodeSpan.className = 'debug-node-id';
            nodeSpan.textContent = log.node_id;
            logContent.appendChild(nodeSpan);
        }
        
        // Add message
        const messageSpan = document.createElement('span');
        messageSpan.className = 'debug-message';
        messageSpan.textContent = log.message;
        logContent.appendChild(messageSpan);
        
        logEntry.appendChild(logTime);
        logEntry.appendChild(logContent);
        logContainer.appendChild(logEntry);
        
        // Scroll to bottom
        logContainer.scrollTop = logContainer.scrollHeight;
    }
    
    // Display workflow execution results
    function displayWorkflowResults(results) {
        const resultsContainer = document.getElementById('execution-results');
        resultsContainer.innerHTML = '';
        
        if (!results || !results.nodes) {
            resultsContainer.innerHTML = '<div class="alert alert-warning">No results returned</div>';
            workflowResultModal.show();
            return;
        }
        
        // Create header with summary
        const header = document.createElement('div');
        
        // Check if there were errors
        const hasErrors = results.errors && results.errors.length > 0;
        const errorCount = hasErrors ? results.errors.length : 0;
        
        header.innerHTML = `
            <div class="d-flex align-items-center mb-3">
                <h5 class="mb-0 me-2">Execution Results</h5>
                <span class="badge ${hasErrors ? 'bg-danger' : 'bg-success'} ms-2">
                    ${hasErrors ? `${errorCount} Error${errorCount > 1 ? 's' : ''}` : 'Success'}
                </span>
                <div class="ms-auto">
                    <small>Completed in ${results.execution_time.toFixed(2)}s</small>
                </div>
            </div>
        `;
        
        // Add error summary if there are errors
        if (hasErrors) {
            const errorSummary = document.createElement('div');
            errorSummary.className = 'alert alert-danger';
            
            let errorContent = '<h6>Errors:</h6><ul>';
            results.errors.forEach(error => {
                const nodeInfo = error.node_id ? `<strong>${error.node_id}</strong>: ` : '';
                errorContent += `<li>${nodeInfo}${error.message}</li>`;
            });
            errorContent += '</ul>';
            
            errorSummary.innerHTML = errorContent;
            header.appendChild(errorSummary);
        }
        
        resultsContainer.appendChild(header);
        
        // Display each node result
        const nodesContainer = document.createElement('div');
        nodesContainer.className = 'nodes-results-container';
        
        for (const [nodeId, nodeResult] of Object.entries(results.nodes)) {
            const node = nodes[nodeId];
            const nodeTypeDef = node ? nodeTypeDefinitions[node.type] : null;
            
            const resultEl = document.createElement('div');
            resultEl.className = `node-result ${nodeResult.status === 'error' ? 'result-error' : 'result-success'}`;
            
            // Result header
            const resultHeader = document.createElement('div');
            resultHeader.className = 'node-result-header';
            resultHeader.innerHTML = `
                <div class="node-icon" style="background-color: ${nodeTypeDef ? nodeTypeDef.color : '#ccc'}; width: 24px; height: 24px; font-size: 0.8rem;">
                    <i class="fas ${nodeTypeDef ? nodeTypeDef.icon : 'fa-cog'}"></i>
                </div>
                <div class="ms-2">
                    <strong>${nodeResult.id}</strong>
                    <div class="small text-muted">${nodeResult.type}</div>
                </div>
                <div class="ms-auto badge ${nodeResult.status === 'error' ? 'bg-danger' : 'bg-success'}">
                    ${nodeResult.status}
                </div>
            `;
            
            // Add execution time
            const timeDiv = document.createElement('div');
            timeDiv.className = 'ms-2 small text-muted';
            timeDiv.textContent = `${nodeResult.execution_time.toFixed(2)}s`;
            resultHeader.appendChild(timeDiv);
            
            // Result body
            const resultBody = document.createElement('div');
            resultBody.className = 'node-result-body';
            
            if (nodeResult.status === 'error') {
                // Show error message
                resultBody.innerHTML = `
                    <div class="text-danger mb-2">
                        <strong>Error:</strong> ${nodeResult.error}
                    </div>
                `;
                
                // Add traceback if available
                if (nodeResult.traceback) {
                    const tracebackDiv = document.createElement('div');
                    tracebackDiv.className = 'traceback-container';
                    
                    const toggleLink = document.createElement('a');
                    toggleLink.href = '#';
                    toggleLink.className = 'traceback-toggle';
                    toggleLink.textContent = 'Show traceback';
                    
                    const tracebackContent = document.createElement('pre');
                    tracebackContent.className = 'traceback-content';
                    tracebackContent.style.display = 'none';
                    tracebackContent.textContent = nodeResult.traceback;
                    
                    toggleLink.addEventListener('click', function(e) {
                        e.preventDefault();
                        if (tracebackContent.style.display === 'none') {
                            tracebackContent.style.display = 'block';
                            toggleLink.textContent = 'Hide traceback';
                        } else {
                            tracebackContent.style.display = 'none';
                            toggleLink.textContent = 'Show traceback';
                        }
                    });
                    
                    tracebackDiv.appendChild(toggleLink);
                    tracebackDiv.appendChild(tracebackContent);
                    resultBody.appendChild(tracebackDiv);
                }
            } else {
                // Format result as JSON with syntax highlighting
                try {
                    let resultOutput;
                    
                    // Check result type and format appropriately
                    if (typeof nodeResult.result === 'object' && nodeResult.result !== null) {
                        resultOutput = formatJson(JSON.stringify(nodeResult.result, null, 2));
                    } else if (typeof nodeResult.result === 'string') {
                        // Check if it's JSON string
                        try {
                            const parsed = JSON.parse(nodeResult.result);
                            resultOutput = formatJson(JSON.stringify(parsed, null, 2));
                        } catch (e) {
                            // Not JSON, display as text
                            resultOutput = nodeResult.result;
                        }
                    } else {
                        // Format other types
                        resultOutput = String(nodeResult.result);
                    }
                    
                    resultBody.innerHTML = resultOutput;
                } catch (e) {
                    resultBody.textContent = 'Error formatting result: ' + e.message;
                }
            }
            
            resultEl.appendChild(resultHeader);
            resultEl.appendChild(resultBody);
            nodesContainer.appendChild(resultEl);
        }
        
        resultsContainer.appendChild(nodesContainer);
        workflowResultModal.show();
    }
    
    // Format JSON with syntax highlighting
    function formatJson(json) {
        // Replace double quotes with spans
        return json
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, function (match) {
                let cls = 'json-number';
                if (/^"/.test(match)) {
                    if (/:$/.test(match)) {
                        cls = 'json-key';
                    } else {
                        cls = 'json-string';
                    }
                } else if (/true|false/.test(match)) {
                    cls = 'json-boolean';
                } else if (/null/.test(match)) {
                    cls = 'json-null';
                }
                return '<span class="' + cls + '">' + match + '</span>';
            });
    }
    
    // Add a function to check if any node has an error
    function hasNodeErrors() {
        return document.querySelectorAll('.node-error').length > 0;
    }
    
    // Setup event handlers once DOM is fully loaded
    setupEventHandlers();
    
    // Click on canvas to deselect nodes
    canvas.addEventListener('click', function(e) {
        if (e.target === canvas) {
            hideConfigPanel();
        }
    });
    
    // Add clear results functionality
    const debugControls = document.querySelector('.debug-controls');
    if (debugControls) {
        // Add clear results button to the debug panel
        const clearResultsBtn = document.createElement('button');
        clearResultsBtn.id = 'clear-results';
        clearResultsBtn.className = 'btn btn-sm btn-outline-danger ms-2';
        clearResultsBtn.innerHTML = '<i class="fas fa-broom"></i> Clear All';
        clearResultsBtn.title = 'Clear node statuses and debug logs';
        
        debugControls.appendChild(clearResultsBtn);
        
        clearResultsBtn.addEventListener('click', function() {
            clearNodeErrorStates();
            clearDebugLogs();
        });
    }
    
    // Initialize jsPlumb when window is fully loaded
    window.addEventListener('load', function() {
        jsPlumbInstance.setContainer(canvas);
    });
});
