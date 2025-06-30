"""
Test suite for the DevOps pipeline demo application.

Tests the main application functionality including the Calculator class
and Flask endpoints.
"""

import pytest
import json
from app import app, Calculator


class TestCalculator:
    """Test cases for the Calculator class."""
    
    def test_add(self):
        """Test addition operation."""
        calc = Calculator()
        assert calc.add(2, 3) == 5
        assert calc.add(-1, 1) == 0
        assert calc.add(0, 0) == 0
        assert calc.add(10.5, 2.5) == 13.0
    
    def test_subtract(self):
        """Test subtraction operation."""
        calc = Calculator()
        assert calc.subtract(5, 3) == 2
        assert calc.subtract(1, 1) == 0
        assert calc.subtract(0, 5) == -5
        assert calc.subtract(10.5, 2.5) == 8.0
    
    def test_multiply(self):
        """Test multiplication operation."""
        calc = Calculator()
        assert calc.multiply(3, 4) == 12
        assert calc.multiply(0, 5) == 0
        assert calc.multiply(-2, 3) == -6
        assert calc.multiply(2.5, 4) == 10.0
    
    def test_divide(self):
        """Test division operation."""
        calc = Calculator()
        assert calc.divide(10, 2) == 5
        assert calc.divide(9, 3) == 3
        assert calc.divide(1, 4) == 0.25
        
    def test_divide_by_zero(self):
        """Test division by zero raises ValueError."""
        calc = Calculator()
        with pytest.raises(ValueError, match="Cannot divide by zero"):
            calc.divide(10, 0)


class TestFlaskApp:
    """Test cases for Flask application endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client for Flask app."""
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_home_endpoint(self, client):
        """Test home endpoint."""
        response = client.get('/')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'message' in data
        assert 'timestamp' in data
        assert 'status' in data
        assert data['status'] == 'healthy'
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get('/health')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert 'timestamp' in data
        assert 'version' in data
    
    def test_info_endpoint(self, client):
        """Test application info endpoint."""
        response = client.get('/info')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'name' in data
        assert 'version' in data
        assert 'endpoints' in data
        assert isinstance(data['endpoints'], list)
    
    def test_calculate_add(self, client):
        """Test calculate endpoint with addition."""
        payload = {
            'operation': 'add',
            'num1': 5,
            'num2': 3
        }
        response = client.post('/calculate', 
                             data=json.dumps(payload),
                             content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['result'] == 8
        assert data['operation'] == 'add'
    
    def test_calculate_subtract(self, client):
        """Test calculate endpoint with subtraction."""
        payload = {
            'operation': 'subtract',
            'num1': 10,
            'num2': 4
        }
        response = client.post('/calculate',
                             data=json.dumps(payload),
                             content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['result'] == 6
    
    def test_calculate_multiply(self, client):
        """Test calculate endpoint with multiplication."""
        payload = {
            'operation': 'multiply',
            'num1': 6,
            'num2': 7
        }
        response = client.post('/calculate',
                             data=json.dumps(payload),
                             content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['result'] == 42
    
    def test_calculate_divide(self, client):
        """Test calculate endpoint with division."""
        payload = {
            'operation': 'divide',
            'num1': 15,
            'num2': 3
        }
        response = client.post('/calculate',
                             data=json.dumps(payload),
                             content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['result'] == 5
    
    def test_calculate_divide_by_zero(self, client):
        """Test calculate endpoint with division by zero."""
        payload = {
            'operation': 'divide',
            'num1': 10,
            'num2': 0
        }
        response = client.post('/calculate',
                             data=json.dumps(payload),
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_calculate_invalid_operation(self, client):
        """Test calculate endpoint with invalid operation."""
        payload = {
            'operation': 'invalid',
            'num1': 5,
            'num2': 3
        }
        response = client.post('/calculate',
                             data=json.dumps(payload),
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_calculate_missing_data(self, client):
        """Test calculate endpoint with missing data."""
        payload = {
            'operation': 'add',
            'num1': 5
            # Missing num2
        }
        response = client.post('/calculate',
                             data=json.dumps(payload),
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_calculate_no_json(self, client):
        """Test calculate endpoint with no JSON data."""
        response = client.post('/calculate')
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert 'error' in data
