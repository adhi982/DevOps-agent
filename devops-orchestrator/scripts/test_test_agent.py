#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test script for the Test Agent.
This script simulates a Kafka message and tests the test agent functionality.
"""

import os
import sys
import json
import tempfile
import shutil
import logging
import importlib.util

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

# Import directly
test_agent_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'agents', 'test_agent', 'main.py')
spec = importlib.util.spec_from_file_location("test_agent_main", test_agent_path)
test_agent_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(test_agent_module)
TestAgent = test_agent_module.TestAgent

from common.kafka_client import KafkaClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_test_agent")

def create_test_repo():
    """Create a test repository with Python test files."""
    temp_dir = tempfile.mkdtemp(prefix="test_pytest_")
    
    # Create a sample module to test
    with open(os.path.join(temp_dir, "sample_module.py"), "w") as f:
        f.write("""#!/usr/bin/env python
# -*- coding: utf-8 -*-

\"\"\"
Sample Python module for testing.
\"\"\"

def add(a, b):
    \"\"\"Add two numbers.\"\"\"
    return a + b

def subtract(a, b):
    \"\"\"Subtract b from a.\"\"\"
    return a - b

def multiply(a, b):
    \"\"\"Multiply two numbers.\"\"\"
    return a * b

def divide(a, b):
    \"\"\"Divide a by b.\"\"\"
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
""")
    
    # Create a test file
    with open(os.path.join(temp_dir, "test_sample_module.py"), "w") as f:
        f.write("""#!/usr/bin/env python
# -*- coding: utf-8 -*-

\"\"\"
Tests for sample_module.py
\"\"\"

import pytest
from sample_module import add, subtract, multiply, divide

def test_add():
    \"\"\"Test the add function.\"\"\"
    assert add(1, 2) == 3
    assert add(-1, 1) == 0
    assert add(0, 0) == 0

def test_subtract():
    \"\"\"Test the subtract function.\"\"\"
    assert subtract(3, 1) == 2
    assert subtract(1, 1) == 0
    assert subtract(0, 5) == -5

def test_multiply():
    \"\"\"Test the multiply function.\"\"\"
    assert multiply(2, 3) == 6
    assert multiply(0, 5) == 0
    assert multiply(-2, 3) == -6

def test_divide():
    \"\"\"Test the divide function.\"\"\"
    assert divide(6, 3) == 2
    assert divide(5, 2) == 2.5
    
    # Test division by zero raises error
    with pytest.raises(ValueError):
        divide(10, 0)
""")
    
    # Create a pytest.ini file
    with open(os.path.join(temp_dir, "pytest.ini"), "w") as f:
        f.write("""[pytest]
python_files = test_*.py
python_functions = test_*
""")
    
    # Initialize a git repo
    os.chdir(temp_dir)
    os.system("git init")
    os.system("git config user.email 'test@example.com'")
    os.system("git config user.name 'Test User'")
    os.system("git add .")
    os.system("git commit -m 'Initial commit'")
    
    return temp_dir

def test_test_agent():
    """Test the Test Agent directly."""
    logger.info("Testing Test Agent...")
    
    # Create a test repo
    repo_dir = create_test_repo()
    logger.info(f"Created test repo at: {repo_dir}")
    
    try:
        # Create a sample message
        message = {
            "pipeline_id": "test-pipeline-456",
            "repository": {
                "clone_url": repo_dir,  # Use local path as "URL"
                "name": "test-repo"
            },
            "branch": "master",
            "event_type": "push"
        }
        
        # Create the agent
        agent = TestAgent()
        
        # Run tests directly on the repo
        test_results = agent.run_tests(repo_dir)
        
        # Print results
        logger.info("Test Results:")
        logger.info(json.dumps(test_results, indent=2))
        
        # Send to Kafka for verification
        try:
            KafkaClient.send_message(
                topic="agent.test",
                message=message,
                key="test-key"
            )
            logger.info("Sent test message to Kafka")
        except Exception as e:
            logger.error(f"Failed to send to Kafka: {e}")
    
    finally:
        # Clean up
        if os.path.exists(repo_dir):
            shutil.rmtree(repo_dir)
            logger.info(f"Cleaned up test repo: {repo_dir}")

if __name__ == "__main__":
    test_test_agent()
