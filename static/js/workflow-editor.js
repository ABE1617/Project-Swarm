document.addEventListener('DOMContentLoaded', function() {
    // Initialize jsPlumb
    const jsPlumbInstance = jsPlumb.getInstance({
        Endpoint: ["Dot", { radius: 4 }],
        Connector: ["Bezier", { curviness: 50 }],
        PaintStyle: { 
            stroke: "#6563ef", 
            strokeWidth: 2 
        },
        HoverPaintStyle: { 
            stroke: "#4caf50", 
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
    }
    
    // NODE OPERATIONS
    
    // Create a new node
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
        
        nodeHeader.appendChild(nodeIcon);
        nodeHeader.appendChild(nodeName);
        
        // Node ports
        const nodePorts = document.createElement('div');
        nodePorts.className = 'node-ports';
        
        // Input ports
        if (nodeTypeDef.inputs && nodeTypeDef.inputs.length > 0) {
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
        
        // Assemble node
        nodeEl.appendChild(nodeHeader);
        nodeEl.appendChild(nodePorts);
        canvas.appendChild(nodeEl);
        
        // Add node to state
        nodes[nodeId] = {
            id: nodeId,
            type: nodeType,
            position: { x, y },
            config: {}
        };
        
        // Make node draggable
        jsPlumbInstance.draggable(nodeId, {
            grid: [10, 10],
            stop: function(event) {
                // Update node position in state
                nodes[nodeId].position.x = parseInt(event.pos[0]);
                nodes[nodeId].position.y = parseInt(event.pos[1]);
            }
        });
        
        // Make end points
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
        
        // Setup connection listeners
        jsPlumbInstance.bind('connection', function(info) {
            // Add connection to state
            connections.push({
                source: info.sourceId,
                target: info.targetId
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
        
        return nodeId;
    }
    
    // Select a node
    function selectNode(nodeId) {
        // Clear any existing selection
        if (selectedNodeId) {
            document.getElementById(selectedNodeId)?.classList.remove('node-selected');
        }
        
        // Update selected node
        selectedNodeId = nodeId;
        
        // Highlight selected node
        const nodeEl = document.getElementById(nodeId);
        if (nodeEl) {
            nodeEl.classList.add('node-selected');
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
    function serializeWorkflow() {
        // Convert nodes object to array
        const nodesArray = Object.values(nodes).map(node => ({
            id: node.id,
            type: node.type,
            config: node.config
        }));
        
        return {
            nodes: nodesArray,
            connections: connections,
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
    
    // Execute the current workflow
    function executeWorkflow() {
        const workflow = serializeWorkflow();
        
        executeWorkflowBtn.disabled = true;
        executeWorkflowBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Executing...';
        
        fetch('/api/run-workflow', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(workflow),
        })
        .then(response => response.json())
        .then(data => {
            // Re-enable button
            executeWorkflowBtn.disabled = false;
            executeWorkflowBtn.innerHTML = '<i class="fas fa-play me-1"></i> Execute';
            
            if (data.success) {
                displayWorkflowResults(data.results);
            } else {
                alert('Error executing workflow: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error('Error executing workflow:', error);
            alert('Error executing workflow');
            
            // Re-enable button
            executeWorkflowBtn.disabled = false;
            executeWorkflowBtn.innerHTML = '<i class="fas fa-play me-1"></i> Execute';
        });
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
        
        // Create header
        const header = document.createElement('div');
        header.innerHTML = '<h5 class="mb-3">Node Results</h5>';
        resultsContainer.appendChild(header);
        
        // Display each node result
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
            
            // Result body
            const resultBody = document.createElement('div');
            resultBody.className = 'node-result-body';
            
            if (nodeResult.status === 'error') {
                resultBody.innerHTML = `<div class="text-danger">${nodeResult.error}</div>`;
            } else {
                // Format result as JSON with syntax highlighting
                const resultJson = JSON.stringify(nodeResult.result, null, 2);
                resultBody.innerHTML = formatJson(resultJson);
            }
            
            resultEl.appendChild(resultHeader);
            resultEl.appendChild(resultBody);
            resultsContainer.appendChild(resultEl);
        }
        
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
    
    // Setup event handlers once DOM is fully loaded
    setupEventHandlers();
    
    // Click on canvas to deselect nodes
    canvas.addEventListener('click', function(e) {
        if (e.target === canvas) {
            hideConfigPanel();
        }
    });
    
    // Initialize jsPlumb when window is fully loaded
    window.addEventListener('load', function() {
        jsPlumbInstance.setContainer(canvas);
    });
});
