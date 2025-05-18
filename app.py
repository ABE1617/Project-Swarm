import os
import json
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
import importlib
import os.path
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Initialize database base class
class Base(DeclarativeBase):
    pass

# Initialize database
db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///swarm.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
db.init_app(app)

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Import execution engine
from execution_engine import execute_workflow
from utils.schema_validator import validate_workflow

# Import models after db initialization
with app.app_context():
    from models import User, Workflow
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('workflow_editor'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists!', 'danger')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered!', 'danger')
            return render_template('register.html')
        
        new_user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# Application routes
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/workflow')
@login_required
def workflow_editor():
    return render_template('workflow.html')

# API endpoints
@app.route('/api/run-workflow', methods=['POST'])
@login_required
def run_workflow():
    import traceback  # Import traceback module for error details
    
    try:
        data = request.json
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Invalid request - missing JSON data',
                'debug_logs': [{
                    'timestamp': datetime.now().isoformat(),
                    'level': 'error',
                    'node_id': None,
                    'message': 'Invalid request - missing JSON data'
                }]
            }), 400
        
        # Add base URL for webhook nodes
        if 'BASE_URL' not in os.environ:
            # Get the request base URL for webhook integration
            base_url = request.url_root.rstrip('/')
            os.environ['BASE_URL'] = base_url
        
        # Validate the workflow structure
        is_valid, errors = validate_workflow(data)
        
        if not is_valid:
            return jsonify({
                'success': False,
                'error': 'Invalid workflow structure',
                'errors': errors,
                'debug_logs': [{
                    'timestamp': datetime.now().isoformat(),
                    'level': 'error',
                    'node_id': None,
                    'message': f'Validation error: {error}' 
                } for error in errors]
            }), 400
        
        # Execute the workflow
        results = execute_workflow(data)
        
        # Check if there were execution errors
        if results.get('errors') and len(results['errors']) > 0:
            app.logger.warning(f"Workflow executed with {len(results['errors'])} errors")
            
            # Return partial success with results and errors
            return jsonify({
                'success': True,  # Still return success to allow the frontend to process the results
                'has_errors': True,
                'results': results
            })
        
        # Return success with full results
        return jsonify({
            'success': True,
            'has_errors': False,
            'results': results
        })
    
    except Exception as e:
        app.logger.error(f"Error executing workflow: {str(e)}")
        app.logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Return error details with debug logs
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc(),
            'debug_logs': [{
                'timestamp': datetime.now().isoformat(),
                'level': 'error',
                'node_id': None,
                'message': f'Server error: {str(e)}'
            }]
        }), 500

@app.route('/api/save-workflow', methods=['POST'])
@login_required
def save_workflow():
    data = request.json
    workflow_name = data.get('name', 'Untitled Workflow')
    workflow_data = data.get('workflow', {})
    
    try:
        # Check if workflow exists
        existing_workflow = Workflow.query.filter_by(
            name=workflow_name, 
            user_id=current_user.id
        ).first()
        
        if existing_workflow:
            # Update existing workflow
            existing_workflow.data = json.dumps(workflow_data)
            db.session.commit()
            return jsonify({
                'success': True,
                'message': f'Workflow "{workflow_name}" updated successfully',
                'id': existing_workflow.id
            })
        else:
            # Create new workflow
            new_workflow = Workflow(
                name=workflow_name,
                data=json.dumps(workflow_data),
                user_id=current_user.id
            )
            db.session.add(new_workflow)
            db.session.commit()
            
            # Also save to filesystem for compatibility
            os.makedirs('workflows', exist_ok=True)
            with open(f'workflows/{current_user.id}_{new_workflow.id}.json', 'w') as f:
                json.dump(workflow_data, f, indent=2)
                
            return jsonify({
                'success': True,
                'message': f'Workflow "{workflow_name}" saved successfully',
                'id': new_workflow.id
            })
    except Exception as e:
        app.logger.error(f"Error saving workflow: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/workflows', methods=['GET'])
@login_required
def get_workflows():
    try:
        workflows = Workflow.query.filter_by(user_id=current_user.id).all()
        return jsonify({
            'success': True,
            'workflows': [
                {
                    'id': workflow.id,
                    'name': workflow.name,
                    'created_at': workflow.created_at.isoformat(),
                    'updated_at': workflow.updated_at.isoformat()
                } for workflow in workflows
            ]
        })
    except Exception as e:
        app.logger.error(f"Error listing workflows: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/workflows/<int:workflow_id>', methods=['GET'])
@login_required
def get_workflow(workflow_id):
    try:
        workflow = Workflow.query.filter_by(
            id=workflow_id,
            user_id=current_user.id
        ).first()
        
        if not workflow:
            return jsonify({
                'success': False,
                'error': 'Workflow not found'
            }), 404
            
        return jsonify({
            'success': True,
            'workflow': {
                'id': workflow.id,
                'name': workflow.name,
                'data': json.loads(workflow.data)
            }
        })
    except Exception as e:
        app.logger.error(f"Error getting workflow: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/workflows/<int:workflow_id>', methods=['DELETE'])
@login_required
def delete_workflow(workflow_id):
    try:
        workflow = Workflow.query.filter_by(
            id=workflow_id,
            user_id=current_user.id
        ).first()
        
        if not workflow:
            return jsonify({
                'success': False,
                'error': 'Workflow not found'
            }), 404
            
        db.session.delete(workflow)
        db.session.commit()
        
        # Also remove file if it exists
        file_path = f'workflows/{current_user.id}_{workflow_id}.json'
        if os.path.exists(file_path):
            os.remove(file_path)
            
        return jsonify({
            'success': True,
            'message': f'Workflow "{workflow.name}" deleted successfully'
        })
    except Exception as e:
        app.logger.error(f"Error deleting workflow: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/webhooks/<path:webhook_path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def handle_webhook(webhook_path):
    """Handle incoming webhook requests for webhook_trigger nodes"""
    try:
        # Import the webhook_trigger module
        try:
            webhook_module = importlib.import_module('control_nodes.webhook_trigger')
        except ImportError:
            return jsonify({
                'error': 'Webhook functionality not available'
            }), 500
        
        # Extract data from the request
        method = request.method
        headers = request.headers
        args = request.args
        
        # Get JSON or form data
        json_data = request.get_json(silent=True)
        form_data = request.form.to_dict() if request.form else None
        
        # Pass to the webhook handler in the module
        if hasattr(webhook_module, 'handle_webhook'):
            response_data, status_code = webhook_module.handle_webhook(
                webhook_path, method, headers, args, json_data, form_data
            )
            return jsonify(response_data), status_code
        else:
            return jsonify({
                'error': 'Webhook handler not implemented'
            }), 501
    
    except Exception as e:
        app.logger.error(f"Error handling webhook request: {str(e)}")
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/api/node-types', methods=['GET'])
@login_required
def get_node_types():
    """Return list of available node types from control_nodes directory"""
    node_types = []
    
    # Get all Python files in the control_nodes directory
    try:
        # Dynamically discover node types
        control_nodes_dir = os.path.join(os.path.dirname(__file__), 'control_nodes')
        for filename in os.listdir(control_nodes_dir):
            if filename.endswith('.py') and not filename.startswith('__'):
                module_name = filename[:-3]  # Remove .py extension
                
                # Import the module to get metadata
                try:
                    module = importlib.import_module(f'control_nodes.{module_name}')
                    
                    # Check if module has required metadata
                    if hasattr(module, 'NODE_TYPE') and hasattr(module, 'NODE_NAME') and hasattr(module, 'NODE_DESCRIPTION'):
                        node_types.append({
                            'type': module.NODE_TYPE,
                            'name': module.NODE_NAME,
                            'description': module.NODE_DESCRIPTION,
                            'color': getattr(module, 'NODE_COLOR', '#5072A7'),
                            'icon': getattr(module, 'NODE_ICON', 'fa-cog'),
                            'config_schema': getattr(module, 'CONFIG_SCHEMA', {})
                        })
                except Exception as e:
                    app.logger.error(f"Error loading module {module_name}: {str(e)}")
        
        return jsonify({
            'success': True,
            'node_types': node_types
        })
    except Exception as e:
        app.logger.error(f"Error getting node types: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
