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
    
    // ZOOM FUNCTIONALITY
    let currentZoom = 1;
    const MIN_ZOOM = 0.1;
    const MAX_ZOOM = 2;
    const ZOOM_STEP = 0.1;
    
    const canvas = document.getElementById('workflow-canvas');
    const zoomInBtn = document.getElementById('zoom-in');
    const zoomOutBtn = document.getElementById('zoom-out');
    const zoomFitBtn = document.getElementById('zoom-fit');
    const zoomLevelDisplay = document.querySelector('.zoom-level');
    
    function updateZoom(newZoom) {
        currentZoom = Math.min(Math.max(newZoom, MIN_ZOOM), MAX_ZOOM);
        canvas.style.transform = `scale(${currentZoom})`;
        zoomLevelDisplay.textContent = `${Math.round(currentZoom * 100)}%`;
        jsPlumbInstance.setZoom(currentZoom);
    }
    
    function zoomIn() {
        updateZoom(currentZoom + ZOOM_STEP);
    }
    
    function zoomOut() {
        updateZoom(currentZoom - ZOOM_STEP);
    }
    
    function zoomFit() {
        // Get all nodes
        const nodes = document.querySelectorAll('.workflow-node');
        if (nodes.length === 0) {
            updateZoom(1); // Reset to 100% if no nodes
            return;
        }
        
        // Calculate bounds
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        nodes.forEach(node => {
            const rect = node.getBoundingClientRect();
            minX = Math.min(minX, rect.left);
            minY = Math.min(minY, rect.top);
            maxX = Math.max(maxX, rect.right);
            maxY = Math.max(maxY, rect.bottom);
        });
        
        // Calculate required scale
        const padding = 50; // Padding around nodes
        const containerWidth = canvas.clientWidth;
        const containerHeight = canvas.clientHeight;
        const contentWidth = maxX - minX + (padding * 2);
        const contentHeight = maxY - minY + (padding * 2);
        
        const scaleX = containerWidth / contentWidth;
        const scaleY = containerHeight / contentHeight;
        const scale = Math.min(scaleX, scaleY, 1); // Don't zoom in past 100%
        
        updateZoom(scale);
    }
    
    // Add zoom event listeners
    zoomInBtn.addEventListener('click', zoomIn);
    zoomOutBtn.addEventListener('click', zoomOut);
    zoomFitBtn.addEventListener('click', zoomFit);
    
    // Add mouse wheel zoom support with Ctrl key
    canvas.addEventListener('wheel', function(e) {
        if (e.ctrlKey) {
            e.preventDefault();
            const delta = e.deltaY < 0 ? ZOOM_STEP : -ZOOM_STEP;
            updateZoom(currentZoom + delta);
        }
    });
    
    // GLOBAL STATE
    let nodes = {};
    let connections = [];
    let selectedNodeId = null;
    let currentWorkflowId = null;
    let currentWorkflowName = "Untitled Workflow";
    let nodeTypeDefinitions = {};
    
    // DOM ELEMENTS
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
    
    // INITIALIZATION
    
    // Fetch node types from server
    fetchNodeTypes().then(types => {
        nodeTypeDefinitions = types;
        initDragAndDrop();
    });
    
    // Copy to clipboard with feedback
    function copyToClipboard(text, element) {
        navigator.clipboard.writeText(text).then(() => {
            // Show copy feedback
            const rect = element.getBoundingClientRect();
            const tooltip = document.createElement('div');
            tooltip.className = 'copy-tooltip';
            tooltip.textContent = 'Copied!';
            tooltip.style.top = `${rect.top - 30}px`;
            tooltip.style.left = `${rect.left + (rect.width / 2) - 30}px`;
            document.body.appendChild(tooltip);
            
            // Show the tooltip
            setTimeout(() => tooltip.classList.add('show'), 10);
            
            // Highlight the element
            const originalBg = element.style.backgroundColor;
            element.style.backgroundColor = '#c3e6cb';
            
            // Remove tooltip and restore styles after delay
            setTimeout(() => {
                tooltip.classList.remove('show');
                setTimeout(() => tooltip.remove(), 300);
                element.style.backgroundColor = originalBg;
            }, 1500);
        }).catch(err => {
            console.error('Failed to copy: ', err);
            // Show error toast
            showConnectionError('Failed to copy to clipboard');
        });
    }
    
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
        
        // Setup click event delegation for variable copying
        document.addEventListener('click', function(e) {
            if (e.target.tagName === 'CODE' && e.target.closest('.var-list')) {
                copyToClipboard(e.target.textContent, e.target);
            }
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
        
        // Input ports - skip for manual_trigger nodes
        if (nodeTypeDef.inputs && nodeTypeDef.inputs.length > 0 && nodeType !== 'manual_trigger') {
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
        
        // Output ports
        if (nodeTypeDef.outputs && nodeTypeDef.outputs.length > 0) {
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
            // Input endpoints - skip for manual trigger
            if (nodeTypeDef.inputs && nodeTypeDef.inputs.length > 0 && nodeType !== 'manual_trigger') {
                jsPlumbInstance.makeTarget(nodeEl.querySelector('.input-handle'), {
                    anchor: 'Left',
                    maxConnections: 1 // Limit to one connection per input
                });
            }
            
            if (nodeTypeDef.outputs && nodeTypeDef.outputs.length > 0) {
                jsPlumbInstance.makeSource(nodeEl.querySelector('.output-handle'), {
                    anchor: 'Right',
                    maxConnections: -1 // Can connect to multiple targets
                });
            }
        }
        
        // Setup connection listeners
        jsPlumbInstance.bind('connection', function(info) {
            // Add connection to state with explicit source and target IDs
            const connection = {
                source: info.source.id,  // Use the actual element IDs
                target: info.target.id,
                sourcePort: info.source.getAttribute('data-port'),
                targetPort: info.target.getAttribute('data-port')
            };
            connections.push(connection);
            
            // Remove guide when first connection is made
            document.querySelector('.canvas-guide')?.remove();
            
            // Log connection for debugging
            console.log('Connection added:', connection);
        });
        
        jsPlumbInstance.bind('connectionDetached', function(info) {
            // Remove connection from state using actual element IDs
            connections = connections.filter(conn => 
                !(conn.source === info.source.id && conn.target === info.target.id));
            
            // Log disconnection for debugging
            console.log('Connection removed:', {
                source: info.source.id,
                target: info.target.id
            });
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
        
        // Add connected nodes output reference section if this node has inputs
        if (nodeTypeDef.inputs && nodeTypeDef.inputs.length > 0 && node.type !== 'manual_trigger') {
            // Find incoming connections
            const incomingConnections = connections.filter(conn => conn.target === nodeId);
            
            if (incomingConnections.length > 0) {
                // Create a section for available output variables
                const outputsSection = document.createElement('div');
                outputsSection.className = 'available-outputs mb-4';
                
                const outputsTitle = document.createElement('h6');
                outputsTitle.className = 'text-muted mb-2';
                outputsTitle.textContent = 'Available Input Variables';
                outputsSection.appendChild(outputsTitle);
                
                // For each incoming connection, show the source node and its available outputs
                incomingConnections.forEach(conn => {
                    const sourceNode = nodes[conn.source];
                    if (!sourceNode) return;
                    
                    const sourceNodeDef = nodeTypeDefinitions[sourceNode.type];
                    if (!sourceNodeDef) return;
                    
                    const sourceInfo = document.createElement('div');
                    sourceInfo.className = 'source-node-info mb-2 p-2 border rounded';
                    
                    // Add source node info
                    const sourceHeader = document.createElement('div');
                    sourceHeader.className = 'd-flex align-items-center mb-2';
                    sourceHeader.innerHTML = `
                        <div class="source-node-icon me-2" style="background-color: ${sourceNodeDef.color}; width: 20px; height: 20px; border-radius: 4px; display: flex; align-items: center; justify-content: center;">
                            <i class="fas ${sourceNodeDef.icon} fa-xs text-white"></i>
                        </div>
                        <div class="source-node-name fw-bold">${sourceNode.id}</div>
                    `;
                    sourceInfo.appendChild(sourceHeader);
                    
                    // Add output variables
                    const varList = document.createElement('div');
                    varList.className = 'var-list small';
                    
                    // Add common output variable for all nodes
                    varList.innerHTML = `<code>{{context.${sourceNode.id}.result}}</code> - Node result output<br>`;
                    
                    // For specific node types, add custom output variables
                    if (sourceNode.type === 'http_request') {
                        varList.innerHTML += `
                            <code>{{context.${sourceNode.id}.status_code}}</code> - Status code<br>
                            <code>{{context.${sourceNode.id}.headers}}</code> - Response headers<br>
                            <code>{{context.${sourceNode.id}.body}}</code> - Response body
                        `;
                    } else if (sourceNode.type === 'read_file') {
                        varList.innerHTML += `
                            <code>{{context.${sourceNode.id}.content}}</code> - File content<br>
                            <code>{{context.${sourceNode.id}.size}}</code> - File size
                        `;
                    }
                    
                    sourceInfo.appendChild(varList);
                    outputsSection.appendChild(sourceInfo);
                });
                
                // Add helper text on how to use variables
                const helperText = document.createElement('div');
                helperText.className = 'text-muted small mt-2';
                helperText.textContent = 'You can use these variables in your configuration by copying the code.';
                outputsSection.appendChild(helperText);
                
                // Add to config form
                configFormEl.appendChild(outputsSection);
                
                // Add a separator
                const separator = document.createElement('hr');
                configFormEl.appendChild(separator);
            }
        }
        
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
        if (!selectedNodeId) {
            return;
        }
        
        const node = nodes[selectedNodeId];
        if (!node) {
            return;
        }
        
        const nodeType = node.type;
        
        // Validate the form first
        const nodeConfigForm = document.querySelector('.node-config');
        if (!window.validateNodeConfigForm(nodeConfigForm, nodeType)) {
            // Show validation alert
            const alertDiv = document.createElement('div');
            alertDiv.className = 'alert alert-danger mb-3';
            alertDiv.textContent = 'Please fill in all required fields correctly.';
            
            // Check if an alert already exists
            const existingAlert = nodeConfigForm.querySelector('.alert-danger');
            if (existingAlert) {
                existingAlert.remove();
            }
            
            // Insert at the top of the form
            nodeConfigForm.insertBefore(alertDiv, nodeConfigForm.firstChild);
            
            // Auto-hide the alert after 5 seconds
            setTimeout(() => {
                alertDiv.classList.add('fade');
                setTimeout(() => alertDiv.remove(), 5000);
            }, 5000);
            
            return;
        }
        
        // Proceed with collecting and applying the config
        const config = {};
        
        // Get all input fields
        const inputs = nodeConfigForm.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            const key = input.name;
            
            if (key) {
                if (input.type === 'checkbox') {
                    config[key] = input.checked;
                } else {
                    config[key] = input.value;
                }
            }
        });
        
        // Save the configuration
        node.config = config;
        
        // Close config panel
        hideConfigPanel();
        
        // Update the node display
        updateNodeDisplay(selectedNodeId);
    }
    
    // WORKFLOW OPERATIONS
    
    // Serialize workflow to JSON
    function serializeWorkflow() {
        // Convert nodes object to array
        const nodesArray = Object.values(nodes).map(node => {
            // Get node element for position
            const nodeElement = document.getElementById(node.id);
            const position = nodeElement ? {
                x: parseInt(nodeElement.style.left) || 0,
                y: parseInt(nodeElement.style.top) || 0
            } : { x: 0, y: 0 };
            
            return {
                id: node.id,
                type: node.type,
                config: node.config || {},
                position: position
            };
        });
        
        // Log the current state for debugging
        console.log('Current Nodes:', nodesArray);
        console.log('Current Connections:', connections);
        
        // Create the workflow data
        const workflowData = {
            nodes: nodesArray,
            connections: connections.map(conn => ({
                source: conn.source,
                target: conn.target
            })),
            variables: {}
        };
        
        // Log the serialized workflow for debugging
        console.log('Serialized Workflow:', workflowData);
        
        return workflowData;
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
                // Use stored position if available, otherwise use default grid layout
                const position = node.position || {};
                const x = position.x !== undefined ? position.x : 100 + (index % 3) * 250;
                const y = position.y !== undefined ? position.y : 100 + Math.floor(index / 3) * 150;
                
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
    
    // Execute the current workflow
    function executeWorkflow() {
        const workflow = serializeWorkflow();
        
        // Check specifically for manual trigger node first (most important validation)
        const triggerNodeTypes = [
            "manual_trigger", "webhook_trigger", "schedule_trigger", 
            "email_trigger", "file_trigger"
        ];
        
        const triggerNodes = workflow.nodes.filter(node => 
            triggerNodeTypes.includes(node.type)
        );
        
        // REMOVED: Do not stop workflow if there are no trigger nodes
        // if (triggerNodes.length === 0) {
        //     showValidationError("Workflow must contain at least one trigger node (like Manual Trigger)");
        //     return;
        // }
        
        // Check if at least one trigger is connected (front-end validation only)
        let triggerConnected = false;
        if (workflow.connections) {
            for (const triggerNode of triggerNodes) {
                if (workflow.connections.some(conn => conn.source === triggerNode.id)) {
                    triggerConnected = true;
                    break;
                }
            }
        }
        

        
        // Additional validation
        const validationResult = validateWorkflow(workflow);
        if (!validationResult.valid) {
            // Show validation errors
            displayValidationErrors(validationResult.errors);
            return;
        }
        
        // Clear any previous error states
        clearNodeErrorStates();
        
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
                    // Add error summary to debug log
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
                
                // Add error to debug log
                addDebugLogEntry({
                    timestamp: new Date().toISOString(),
                    level: 'error',
                    node_id: null,
                    message: `Error executing workflow: ${errorMessage}`
                });
                
                // Show error in debug panel
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
            // Hide progress bar
            hideExecutionProgress();
            
            // Re-enable button
            executeWorkflowBtn.disabled = false;
            executeWorkflowBtn.innerHTML = '<i class="fas fa-play me-1"></i> Execute';
            
            console.error('Error executing workflow:', error);
            
            // Add error to debug log
            addDebugLogEntry({
                timestamp: new Date().toISOString(),
                level: 'error',
                node_id: null,
                message: `Network error: ${error.message}`
            });
        });
    }
    
    // Client-side workflow validation
    function validateWorkflow(workflow) {
        const errors = [];
        
        // Check if workflow has nodes
        if (!workflow.nodes || workflow.nodes.length === 0) {
            errors.push("Workflow must contain at least one node");
            return { valid: false, errors };
        }
        
        // Create node lookup map
        const nodes = {};
        workflow.nodes.forEach(node => {
            nodes[node.id] = node;
        });
        
        // Check nodes that should have only one input
        const singleInputNodeTypes = [
            "http_request", "write_file", "read_file", "email_send", "gmail_send", 
            "save_to_sheets", "save_to_drive", "webhook_response", "set_variable",
            "wait", "data_transform"
        ];
        
        // Count input connections for each node
        const inputConnectionCounts = {};
        if (workflow.connections) {
            workflow.connections.forEach(conn => {
                if (!inputConnectionCounts[conn.target]) {
                    inputConnectionCounts[conn.target] = 0;
                }
                inputConnectionCounts[conn.target]++;
            });
        }
        
        // Check for multiple input violations
        workflow.nodes.forEach(node => {
            if (singleInputNodeTypes.includes(node.type) && 
                inputConnectionCounts[node.id] && 
                inputConnectionCounts[node.id] > 1) {
                errors.push(`Node '${node.id}' (${getNodeTypeName(node.type)}) can only have one input connection`);
            }
        });
        
        // Check required configuration fields
        workflow.nodes.forEach(node => {
            const config = node.config || {};
            
            // HTTP Request node requires URL
            if (node.type === 'http_request' && !config.url) {
                errors.push(`Node '${node.id}' (HTTP Request) requires a URL`);
            }
            
            // Email nodes require to, subject, and body
            else if (node.type === 'email_send') {
                ['to', 'subject', 'body'].forEach(field => {
                    if (!config[field]) {
                        errors.push(`Node '${node.id}' (Email Send) requires '${field}'`);
                    }
                });
            }
            
            // File operations require path
            else if (['write_file', 'read_file'].includes(node.type) && !config.path) {
                errors.push(`Node '${node.id}' (${getNodeTypeName(node.type)}) requires a file path`);
            }
            
            // Write file needs content
            else if (node.type === 'write_file' && !config.content) {
                errors.push(`Node '${node.id}' (Write File) requires content`);
            }
        });
        
        return {
            valid: errors.length === 0,
            errors
        };
    }
    
    // Helper to get readable node type name
    function getNodeTypeName(nodeType) {
        const nodeTypeDef = nodeTypeDefinitions[nodeType];
        return nodeTypeDef ? nodeTypeDef.name : nodeType;
    }
    
    // Display validation errors
    function displayValidationErrors(errors) {
        // Clear previous debug logs
        clearDebugLogs();
        
        // Switch to debug tab
        document.getElementById('debug-tab').click();
        
        // Add validation error header
        addDebugLogEntry({
            timestamp: new Date().toISOString(),
            level: 'error',
            node_id: null,
            message: 'Workflow Validation Failed'
        });
        
        // Add each error
        errors.forEach(error => {
            addDebugLogEntry({
                timestamp: new Date().toISOString(),
                level: 'error',
                node_id: null,
                message: error
            });
        });
        
        // Display error toast
        const toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) {
            return;
        }
        
        const toast = document.createElement('div');
        toast.className = 'toast align-items-center text-white bg-danger border-0';
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <strong>Validation Error</strong>: ${errors[0]} ${errors.length > 1 ? `(+${errors.length - 1} more)` : ''}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        
        toastContainer.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast, { autohide: true, delay: 5000 });
        bsToast.show();
        
        // Remove toast once hidden
        toast.addEventListener('hidden.bs.toast', function() {
            toast.remove();
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
                
                // Add click handler to show debug tab and highlight the error
                errorBadge.addEventListener('click', (e) => {
                    e.stopPropagation(); // Don't select the node
                    
                    // Switch to debug tab
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
                });
                
                nodeEl.appendChild(errorBadge);
            } else if (status === 'success') {
                // If node was successful, remove error class
                nodeEl.classList.remove('node-error');
            }
        });
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
                // Check if it's an HTTP Request node and display specific fields
                if (nodeResult.type === 'http_request' && nodeResult.result) {
                    let httpResultHtml = '<h6>HTTP Response:</h6>';
                    
                    if (nodeResult.result.status_code) {
                        httpResultHtml += `<p><strong>Status Code:</strong> ${nodeResult.result.status_code}</p>`;
                    }
                    
                    if (nodeResult.result.headers) {
                        httpResultHtml += '<h6>Headers:</h6><pre class="json-content">' + formatJson(JSON.stringify(nodeResult.result.headers, null, 2)) + '</pre>';
                    }
                    
                    if (nodeResult.result.body) {
                         // Check if body is JSON
                        try {
                            const bodyJson = JSON.parse(nodeResult.result.body);
                            httpResultHtml += '<h6>Body:</h6><pre class="json-content">' + formatJson(JSON.stringify(bodyJson, null, 2)) + '</pre>';
                        } catch (e) {
                            // Not JSON, display as plain text
                            httpResultHtml += '<h6>Body:</h6><pre class="plain-text">' + nodeResult.result.body + '</pre>';
                        }
                    }
                    
                    resultBody.innerHTML = httpResultHtml;
                } else {
                    // Format other node results as JSON with syntax highlighting
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

    // Add connection validation for single input nodes
    jsPlumbInstance.bind("beforeDrop", function(info) {
        const targetId = info.targetId;
        const sourceId = info.sourceId;
        
        // Prevent nodes from connecting to themselves
        if (targetId === sourceId) {
            showConnectionError("Nodes cannot connect to themselves");
            return false;
        }
        
        // Get node types
        const targetNode = document.getElementById(targetId);
        const sourceNode = document.getElementById(sourceId);
        
        if (!targetNode || !sourceNode) {
            return false;
        }
        
        const targetNodeType = targetNode.dataset.nodeType;
        
        // List of node types that can only have one input
        const singleInputNodeTypes = [
            "http_request", "write_file", "read_file", "email_send", "gmail_send", 
            "save_to_sheets", "save_to_drive", "webhook_response", "set_variable",
            "wait", "data_transform"
        ];
        
        // Check if target node can only have one input
        if (singleInputNodeTypes.includes(targetNodeType)) {
            // Count existing connections to this target
            const connections = jsPlumbInstance.getConnections({
                target: targetId
            });
            
            // If there's already a connection, prevent the new one
            if (connections.length > 0) {
                const nodeTypeName = getNodeTypeName(targetNodeType);
                showConnectionError(`${nodeTypeName} nodes can only have one input connection`);
                return false;
            }
        }
        
        return true;
    });

    // Display connection error message
    function showConnectionError(message) {
        const toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) {
            return;
        }
        
        const toast = document.createElement('div');
        toast.className = 'toast align-items-center text-white bg-danger border-0';
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <strong>Connection Error</strong>: ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        
        toastContainer.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast, { autohide: true, delay: 3000 });
        bsToast.show();
        
        // Remove toast once hidden
        toast.addEventListener('hidden.bs.toast', function() {
            toast.remove();
        });
    }

    // Helper function to show a single validation error
    function showValidationError(errorMessage) {
        // Clear previous debug logs
        clearDebugLogs();
        
        // Switch to debug tab
        document.getElementById('debug-tab').click();
        
        // Add validation error header
        addDebugLogEntry({
            timestamp: new Date().toISOString(),
            level: 'error',
            node_id: null,
            message: 'Workflow Validation Failed'
        });
        
        // Add the error
        addDebugLogEntry({
            timestamp: new Date().toISOString(),
            level: 'error',
            node_id: null,
            message: errorMessage
        });
        
        // Display error toast
        const toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) {
            return;
        }
        
        const toast = document.createElement('div');
        toast.className = 'toast align-items-center text-white bg-danger border-0';
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <strong>Validation Error</strong>: ${errorMessage}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        
        toastContainer.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast, { autohide: true, delay: 5000 });
        bsToast.show();
        
        // Remove toast once hidden
        toast.addEventListener('hidden.bs.toast', function() {
            toast.remove();
        });
    }
});
