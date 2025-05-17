// Node type definitions and configuration schemas
const nodeTypes = {
    http_request: {
        name: 'HTTP Request',
        description: 'Make HTTP requests to APIs and web services',
        color: '#61affe',
        icon: 'fa-globe',
        inputs: ['trigger'],
        outputs: ['result'],
        configSchema: {
            url: {
                type: 'string',
                title: 'URL',
                description: 'URL to make the request to',
                required: true
            },
            method: {
                type: 'string',
                title: 'Method',
                description: 'HTTP Method',
                enum: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'],
                default: 'GET',
                required: true
            },
            headers: {
                type: 'object',
                title: 'Headers',
                description: 'HTTP Headers to include with the request'
            },
            params: {
                type: 'object',
                title: 'Query Parameters',
                description: 'URL query parameters'
            },
            body: {
                type: 'string',
                title: 'Request Body',
                description: 'Body to send with the request (for POST, PUT, etc.)'
            }
        }
    },
    write_file: {
        name: 'Write File',
        description: 'Write data to a file on the server',
        color: '#4caf50',
        icon: 'fa-file',
        inputs: ['trigger'],
        outputs: ['result'],
        configSchema: {
            path: {
                type: 'string',
                title: 'File Path',
                description: 'Path to write the file (relative to workspace)',
                required: true
            },
            content: {
                type: 'string',
                title: 'Content',
                description: 'Content to write to the file',
                required: true
            },
            mode: {
                type: 'string',
                title: 'Write Mode',
                description: 'File write mode',
                enum: ['overwrite', 'append'],
                default: 'overwrite'
            }
        }
    },
    data_transform: {
        name: 'Data Transform',
        description: 'Transform, filter and manipulate data',
        color: '#ff9800',
        icon: 'fa-filter',
        inputs: ['trigger'],
        outputs: ['result'],
        configSchema: {
            operation: {
                type: 'string',
                title: 'Operation',
                description: 'Type of transformation to perform',
                enum: ['filter', 'map', 'sort', 'select', 'custom'],
                default: 'filter',
                required: true
            },
            input: {
                type: 'string',
                title: 'Input',
                description: 'Path to the input data in context (e.g., nodeId.response)',
                required: true
            },
            filter_condition: {
                type: 'string',
                title: 'Filter Condition',
                description: "JavaScript-like condition for filtering (e.g., 'item.age > 18')",
                showIf: {
                    operation: 'filter'
                }
            },
            map_expression: {
                type: 'string',
                title: 'Map Expression',
                description: "Expression for mapping (e.g., '{name: item.name, age: item.age}')",
                showIf: {
                    operation: 'map'
                }
            },
            sort_key: {
                type: 'string',
                title: 'Sort Key',
                description: "Key to sort by (e.g., 'name')",
                showIf: {
                    operation: 'sort'
                }
            },
            select_keys: {
                type: 'array',
                title: 'Select Keys',
                description: 'List of keys to select from objects',
                showIf: {
                    operation: 'select'
                }
            }
        }
    },
    javascript_code: {
        name: 'JavaScript Code',
        description: 'Run JavaScript code',
        color: '#f48c42',
        icon: 'fa-code',
        inputs: ['trigger'],
        outputs: ['result'],
        configSchema: {
            code: {
                type: 'code',
                title: 'Code',
                description: 'JavaScript code to execute',
                language: 'javascript',
                required: true
            },
            input_data: {
                type: 'object',
                title: 'Input Data',
                description: 'Input data for the code'
            }
        }
    },
    email_send: {
        name: 'Send Email',
        description: 'Send emails using SMTP',
        color: '#9c27b0',
        icon: 'fa-envelope',
        inputs: ['trigger'],
        outputs: ['result'],
        configSchema: {
            to: {
                type: 'string',
                title: 'To',
                description: 'Recipient email address',
                required: true
            },
            subject: {
                type: 'string',
                title: 'Subject',
                description: 'Email subject line',
                required: true
            },
            body: {
                type: 'string',
                title: 'Body',
                description: 'Email body content',
                required: true
            },
            html: {
                type: 'boolean',
                title: 'HTML Email',
                description: 'Send as HTML email',
                default: false
            }
        }
    }
};

// Helper function to create configuration form fields based on schema
function createFormField(key, schema) {
    const formGroup = document.createElement('div');
    formGroup.className = 'form-group';
    
    const label = document.createElement('label');
    label.className = 'form-label';
    label.setAttribute('for', key);
    label.textContent = schema.title || key;
    formGroup.appendChild(label);
    
    if (schema.description) {
        const description = document.createElement('div');
        description.className = 'form-description';
        description.textContent = schema.description;
        formGroup.appendChild(description);
    }
    
    let input;
    
    if (schema.type === 'string' && schema.enum) {
        // Select field for enum types
        input = document.createElement('select');
        input.className = 'form-select';
        
        schema.enum.forEach(option => {
            const optionEl = document.createElement('option');
            optionEl.value = option;
            optionEl.textContent = option;
            input.appendChild(optionEl);
        });
        
        if (schema.default) {
            input.value = schema.default;
        }
    } else if (schema.type === 'boolean') {
        // Checkbox for boolean types
        const checkGroup = document.createElement('div');
        checkGroup.className = 'form-check';
        
        input = document.createElement('input');
        input.className = 'form-check-input';
        input.type = 'checkbox';
        input.id = key;
        input.name = key;
        
        if (schema.default) {
            input.checked = schema.default;
        }
        
        const checkLabel = document.createElement('label');
        checkLabel.className = 'form-check-label';
        checkLabel.setAttribute('for', key);
        checkLabel.textContent = schema.title || key;
        
        checkGroup.appendChild(input);
        checkGroup.appendChild(checkLabel);
        
        formGroup.innerHTML = '';
        formGroup.appendChild(checkGroup);
        
        return formGroup;
    } else if (schema.type === 'object') {
        // Textarea for JSON objects
        input = document.createElement('textarea');
        input.className = 'form-control';
        input.rows = 4;
        input.placeholder = '{\n  "key": "value"\n}';
    } else if (schema.type === 'array') {
        // Textarea for arrays
        input = document.createElement('textarea');
        input.className = 'form-control';
        input.rows = 4;
        input.placeholder = '[\n  "item1",\n  "item2"\n]';
    } else if (schema.type === 'code') {
        // Textarea for code
        input = document.createElement('textarea');
        input.className = 'form-control code-editor';
        input.rows = 8;
        input.placeholder = '// Write your code here';
    } else {
        // Default to text input
        input = document.createElement('input');
        input.className = 'form-control';
        input.type = 'text';
        
        if (schema.default) {
            input.value = schema.default;
        }
    }
    
    input.id = key;
    input.name = key;
    
    if (schema.required) {
        input.required = true;
    }
    
    formGroup.appendChild(input);
    return formGroup;
}

// Load node types from server or use the static definitions
function fetchNodeTypes() {
    return new Promise((resolve, reject) => {
        fetch('/api/node-types')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Merge server-provided node types with client defaults
                    const serverNodeTypes = {};
                    data.node_types.forEach(nodeType => {
                        serverNodeTypes[nodeType.type] = {
                            name: nodeType.name,
                            description: nodeType.description,
                            color: nodeType.color,
                            icon: nodeType.icon,
                            inputs: ['trigger'], // Default
                            outputs: ['result'], // Default
                            configSchema: nodeType.config_schema || {}
                        };
                    });
                    
                    // Use server types, fall back to static types if missing
                    resolve(Object.assign({}, nodeTypes, serverNodeTypes));
                } else {
                    // Fall back to static definitions if API fails
                    console.warn('Failed to fetch node types from server, using default types');
                    resolve(nodeTypes);
                }
            })
            .catch(error => {
                console.error('Error fetching node types:', error);
                resolve(nodeTypes); // Fall back to static definitions
            });
    });
}
