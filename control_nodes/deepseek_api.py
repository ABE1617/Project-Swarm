# DeepSeek API Node for Project Swarm
import os
import json
import requests

# Node Metadata
NODE_TYPE = "deepseek_api"
NODE_NAME = "DeepSeek API"
NODE_DESCRIPTION = "Call DeepSeek's AI models to generate text"
NODE_COLOR = "#7b68ee"
NODE_ICON = "fa-robot"

# Configuration Schema
CONFIG_SCHEMA = {
    "api_key": {
        "type": "string",
        "title": "API Key",
        "description": "DeepSeek API key (keep secure)",
        "required": True
    },
    "model": {
        "type": "string",
        "title": "Model",
        "description": "DeepSeek model to use",
        "enum": ["deepseek-chat", "deepseek-coder", "deepseek-v2"],
        "default": "deepseek-chat",
        "required": True
    },
    "messages": {
        "type": "array",
        "title": "Messages",
        "description": "Array of messages in the conversation",
        "required": True
    },
    "system_message": {
        "type": "string",
        "title": "System Message",
        "description": "Optional system message to set the behavior of the assistant"
    },
    "temperature": {
        "type": "number",
        "title": "Temperature",
        "description": "Controls randomness (0-1), lower is more deterministic",
        "default": 0.7
    },
    "max_tokens": {
        "type": "number",
        "title": "Max Tokens",
        "description": "Maximum number of tokens to generate",
        "default": 1000
    }
}

def run(config, context):
    """
    Calls the DeepSeek API to generate text
    
    Args:
        config (dict): Configuration for the API call
        context (dict): Shared context from previous nodes
        
    Returns:
        dict: API response with generated text
    """
    api_key = config.get('api_key', os.environ.get('DEEPSEEK_API_KEY'))
    if not api_key:
        raise ValueError("DeepSeek API key is required. Either provide it in the configuration or set the DEEPSEEK_API_KEY environment variable.")
    
    model = config.get('model', 'deepseek-chat')
    messages_input = config.get('messages', [])
    system_message = config.get('system_message', '')
    temperature = float(config.get('temperature', 0.7))
    max_tokens = int(config.get('max_tokens', 1000))
    
    # Format messages
    messages = []
    
    # Add system message if provided
    if system_message:
        messages.append({"role": "system", "content": system_message})
    
    # Add user messages
    if isinstance(messages_input, list):
        messages.extend(messages_input)
    elif isinstance(messages_input, str):
        # If a simple string is provided, treat it as a user message
        messages.append({"role": "user", "content": messages_input})
    
    # Prepare API request
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    # DeepSeek API endpoint
    api_url = "https://api.deepseek.com/v1/chat/completions"
    
    # Make API request
    try:
        response = requests.post(
            api_url,
            headers=headers,
            json=payload
        )
        
        # Parse response
        if response.status_code == 200:
            response_data = response.json()
            
            # Extract the assistant's message
            assistant_message = response_data['choices'][0]['message']['content']
            
            return {
                'response': assistant_message,
                'full_response': response_data,
                'model': model,
                'usage': response_data.get('usage', {})
            }
        else:
            error_info = response.json() if response.content else {"error": f"HTTP error {response.status_code}"}
            raise Exception(f"DeepSeek API Error: {error_info}")
    
    except Exception as e:
        raise Exception(f"Error calling DeepSeek API: {str(e)}")