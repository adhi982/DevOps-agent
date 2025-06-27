#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test the build agent with a public GitHub repository.
"""

import os
import sys
import json
import logging

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from common.kafka_client import KafkaClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_with_real_docker_repo")

def test_with_real_repo():
    """Test the build agent with a real GitHub repository containing a Dockerfile."""
    logger.info("Testing Build Agent with a real repository...")
    
    # Create a sample message with a real public repo that has a Dockerfile
    message = {
        "pipeline_id": "real-build-123",
        "repository": {
            "clone_url": "https://github.com/docker/getting-started",
            "name": "docker-getting-started"
        },
        "branch": "master",  # Changed from 'main' to 'master'
        "event_type": "push",
        "docker": {
            "image_name": "docker-getting-started",
            "tag": "test",
            "dockerfile": "app/Dockerfile",
            "push": False
        }
    }
    
    # Send to Kafka
    try:
        KafkaClient.send_message(
            topic="agent.build",
            message=message,
            key="real-build-test"
        )
        logger.info("Sent test message to Kafka for real repository")
    except Exception as e:
        logger.error(f"Failed to send to Kafka: {e}")

if __name__ == "__main__":
    test_with_real_repo()
