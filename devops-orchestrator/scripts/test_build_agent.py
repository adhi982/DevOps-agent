#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test script for the Build Agent.
This script simulates a Kafka message and tests the build agent functionality.
"""

import os
import sys
import json
import tempfile
import shutil
import logging
import importlib.util
import time

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

# Import directly
build_agent_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'agents', 'build_agent', 'main.py')
spec = importlib.util.spec_from_file_location("build_agent_main", build_agent_path)
build_agent_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_agent_module)
BuildAgent = build_agent_module.BuildAgent

from common.kafka_client import KafkaClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_build_agent")

def create_test_repo():
    """Create a test repository with a simple Dockerfile."""
    temp_dir = tempfile.mkdtemp(prefix="test_build_")
    
    # Create a simple Dockerfile
    with open(os.path.join(temp_dir, "Dockerfile"), "w") as f:
        f.write("""FROM python:3.9-slim
WORKDIR /app
COPY . .
CMD ["python", "-c", "print('Hello from Docker!')"]
""")
    
    # Create a simple Python app
    with open(os.path.join(temp_dir, "app.py"), "w") as f:
        f.write("""#!/usr/bin/env python
# -*- coding: utf-8 -*-

print("Hello from the test application!")
""")
    
    # Initialize a git repo
    os.chdir(temp_dir)
    os.system("git init")
    os.system("git config user.email 'test@example.com'")
    os.system("git config user.name 'Test User'")
    os.system("git add .")
    os.system("git commit -m 'Initial commit'")
    
    return temp_dir

def test_build_docker_image(agent, repo_dir):
    """Test building a Docker image directly."""
    image_name = "test-build-agent"
    image_tag = str(int(time.time()))  # Use timestamp as tag for uniqueness
    
    build_results = agent.build_docker_image(
        repo_dir=repo_dir,
        image_name=image_name,
        image_tag=image_tag,
        dockerfile_path="Dockerfile"
    )
    
    logger.info("Build Results:")
    logger.info(json.dumps(build_results, indent=2))
    
    return build_results

def test_build_agent():
    """Test the Build Agent directly."""
    logger.info("Testing Build Agent...")
    
    # Create a test repo
    repo_dir = create_test_repo()
    logger.info(f"Created test repo at: {repo_dir}")
    
    try:
        # Create the agent
        agent = BuildAgent()
        
        # Test direct Docker build
        if agent.docker_client is not None:
            build_results = test_build_docker_image(agent, repo_dir)
            
            # Create a sample message for Kafka
            if build_results.get('success'):
                message = {
                    "pipeline_id": "test-build-789",
                    "repository": {
                        "clone_url": repo_dir,  # Use local path as "URL"
                        "name": "test-build-repo"
                    },
                    "branch": "master",
                    "event_type": "push",
                    "docker": {
                        "image_name": "test-pipeline-image",
                        "tag": "test-tag",
                        "push": False
                    }
                }
                
                # Send to Kafka for verification
                try:
                    KafkaClient.send_message(
                        topic="agent.build",
                        message=message,
                        key="test-key"
                    )
                    logger.info("Sent test message to Kafka")
                except Exception as e:
                    logger.error(f"Failed to send to Kafka: {e}")
            else:
                logger.error("Build failed, skipping Kafka message")
        else:
            logger.error("Docker client initialization failed, skipping tests")
    
    finally:
        # Clean up
        if os.path.exists(repo_dir):
            shutil.rmtree(repo_dir)
            logger.info(f"Cleaned up test repo: {repo_dir}")

if __name__ == "__main__":
    test_build_agent()
