"""
Simple Flask web application for DevOps pipeline demonstration.

This application provides basic HTTP endpoints and demonstrates
best practices for Python web development.
"""

from flask import Flask, jsonify, request
import os
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')


class Calculator:
    """Simple calculator class for demonstration."""
    
    @staticmethod
    def add(a: float, b: float) -> float:
        """Add two numbers."""
        return a + b
    
    @staticmethod
    def subtract(a: float, b: float) -> float:
        """Subtract second number from first."""
        return a - b
    
    @staticmethod
    def multiply(a: float, b: float) -> float:
        """Multiply two numbers."""
        return a * b
    
    @staticmethod
    def divide(a: float, b: float) -> float:
        """Divide first number by second."""
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b


@app.route('/')
def home():
    """Home endpoint."""
    return jsonify({
        'message': 'Welcome to the DevOps Pipeline Demo App',
        'timestamp': datetime.now().isoformat(),
        'status': 'healthy'
    })


@app.route('/health')
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })


@app.route('/calculate', methods=['POST'])
def calculate():
    """Calculate endpoint for basic math operations."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        operation = data.get('operation')
        num1 = data.get('num1')
        num2 = data.get('num2')
        
        if not all([operation, num1 is not None, num2 is not None]):
            return jsonify({
                'error': 'Missing required fields: operation, num1, num2'
            }), 400
        
        calc = Calculator()
        
        if operation == 'add':
            result = calc.add(num1, num2)
        elif operation == 'subtract':
            result = calc.subtract(num1, num2)
        elif operation == 'multiply':
            result = calc.multiply(num1, num2)
        elif operation == 'divide':
            result = calc.divide(num1, num2)
        else:
            return jsonify({
                'error': 'Invalid operation. Use: add, subtract, multiply, divide'
            }), 400
        
        return jsonify({
            'operation': operation,
            'num1': num1,
            'num2': num2,
            'result': result,
            'timestamp': datetime.now().isoformat()
        })
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Calculation error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/info')
def app_info():
    """Application information endpoint."""
    return jsonify({
        'name': 'DevOps Pipeline Demo',
        'version': '1.0.0',
        'description': 'Simple Flask app for demonstrating CI/CD pipeline',
        'endpoints': [
            {'path': '/', 'method': 'GET', 'description': 'Home page'},
            {'path': '/health', 'method': 'GET', 'description': 'Health check'},
            {'path': '/calculate', 'method': 'POST', 'description': 'Math operations'},
            {'path': '/info', 'method': 'GET', 'description': 'App information'}
        ]
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting application on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
