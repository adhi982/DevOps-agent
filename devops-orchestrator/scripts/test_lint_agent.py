#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test script for the Lint Agent.
This script simulates a Kafka message and tests the lint agent functionality.
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
lint_agent_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'agents', 'lint_agent', 'main.py')
spec = importlib.util.spec_from_file_location("lint_agent_main", lint_agent_path)
lint_agent_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lint_agent_module)
LintAgent = lint_agent_module.LintAgent

from common.kafka_client import KafkaClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_lint_agent")

def create_test_repo():
    """Create a test repository with Python files for linting."""
    temp_dir = tempfile.mkdtemp(prefix="test_lint_")
    
    # Create a sample Python file with some lint issues
    with open(os.path.join(temp_dir, "sample.py"), "w") as f:
        f.write("""#!/usr/bin/env python
# -*- coding: utf-8 -*-

\"\"\"
Sample Python file with some lint issues.
\"\"\"

import sys, os  # Multiple imports on one line

def hello_world():
    \"\"\"Print hello world.\"\"\"
    print ("Hello World!")  # Extra space after print

x = 10  # No constant naming convention

class BadClass():  # Old-style class definition
    def __init__(self, name):
        self.name = name
    
    def say_hello(self):
        print("Hello, " + self.name + "!")  # String concatenation instead of formatting

if __name__ == "__main__":
    hello_world()
    obj = BadClass("World")
    obj.say_hello()
""")
    
    # Initialize a git repo
    os.chdir(temp_dir)
    os.system("git init")
    os.system("git config user.email 'test@example.com'")
    os.system("git config user.name 'Test User'")
    os.system("git add sample.py")
    os.system("git commit -m 'Initial commit'")
    
    return temp_dir

def test_lint_agent():
    """Test the Lint Agent directly."""
    logger.info("Testing Lint Agent...")
    
    # Create a test repo
    repo_dir = create_test_repo()
    logger.info(f"Created test repo at: {repo_dir}")
    
    try:
        # Create a sample message
        message = {
            "pipeline_id": "test-pipeline-123",
            "repository": {
                "clone_url": repo_dir,  # Use local path as "URL"
                "name": "test-repo"
            },
            "branch": "master",
            "event_type": "push"
        }
        
        # Create the agent
        agent = LintAgent()
        
        # Run pylint directly on the repo
        lint_results = agent.run_pylint(repo_dir)
        
        # Print results
        logger.info("Lint Results:")
        logger.info(json.dumps(lint_results, indent=2))
        
        # Send to Kafka for verification
        try:
            KafkaClient.send_message(
                topic="agent.lint",
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
    test_lint_agent()
