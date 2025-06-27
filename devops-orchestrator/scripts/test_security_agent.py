#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test script for the Security Agent.
This script simulates a Kafka message and tests the security scanning functionality.
"""

import os
import sys
import json
import logging
import time
import random

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from common.kafka_client import KafkaClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_security_agent")

def test_with_standard_image():
    """Test the Security Agent with a standard Docker Hub image."""
    logger.info("Testing Security Agent with a standard image...")
    
    # Create a sample message for a small, common image
    message = {
        "pipeline_id": f"test-security-{random.randint(1000, 9999)}",
        "image": {
            "name": "python",
            "tag": "3.9-slim"
        },
        "scan_options": {
            "severity": "CRITICAL,HIGH",
            "timeout": 300,  # 5 minutes
            "format": "json"
        }
    }
    
    # Send to Kafka
    try:
        KafkaClient.send_message(
            topic="agent.security",
            message=message,
            key="test-security-standard"
        )
        logger.info("Sent test message to Kafka for standard image")
        return True
    except Exception as e:
        logger.error(f"Failed to send to Kafka: {e}")
        return False

def test_with_vulnerable_image():
    """Test the Security Agent with a known vulnerable image."""
    logger.info("Testing Security Agent with a vulnerable image...")
    
    # Use an older image likely to have known vulnerabilities
    message = {
        "pipeline_id": f"test-security-vuln-{random.randint(1000, 9999)}",
        "image": {
            "name": "node",
            "tag": "14.0"  # Older version likely to have vulnerabilities
        },
        "scan_options": {
            "severity": "CRITICAL,HIGH",
            "timeout": 300,
            "format": "json"
        }
    }
    
    # Send to Kafka
    try:
        KafkaClient.send_message(
            topic="agent.security",
            message=message,
            key="test-security-vulnerable"
        )
        logger.info("Sent test message to Kafka for vulnerable image")
        return True
    except Exception as e:
        logger.error(f"Failed to send to Kafka: {e}")
        return False

def test_with_local_image():
    """Test the Security Agent with a locally built image."""
    logger.info("Testing Security Agent with a local image...")
    
    # Use a recently built local image
    # This assumes a recent build process has created an image
    local_images = [
        "test-build-agent:latest",
        "test-pipeline-image:latest",
        "docker-getting-started:test"
    ]
    
    # Try to find an existing local image to scan
    image_name = None
    image_tag = "latest"
    
    for image in local_images:
        if ":" in image:
            name, tag = image.split(":")
        else:
            name, tag = image, "latest"
            
        # Check if this image exists by running docker inspect
        result = os.system(f"docker image inspect {name}:{tag} > nul 2>&1")
        if result == 0:
            image_name = name
            image_tag = tag
            break
    
    if not image_name:
        logger.warning("No local test images found. Using a public image instead.")
        image_name = "nginx"
        image_tag = "latest"
    
    message = {
        "pipeline_id": f"test-security-local-{random.randint(1000, 9999)}",
        "image": {
            "name": image_name,
            "tag": image_tag
        },
        "scan_options": {
            "severity": "CRITICAL,HIGH,MEDIUM",
            "timeout": 300,
            "format": "json"
        }
    }
    
    # Send to Kafka
    try:
        KafkaClient.send_message(
            topic="agent.security",
            message=message,
            key="test-security-local"
        )
        logger.info(f"Sent test message to Kafka for local image: {image_name}:{image_tag}")
        return True
    except Exception as e:
        logger.error(f"Failed to send to Kafka: {e}")
        return False

def listen_for_results(timeout=600):
    """Listen for results on the agent.results topic."""
    logger.info(f"Listening for results for {timeout} seconds...")
    
    start_time = time.time()
    results_received = 0
    
    def result_handler(message):
        nonlocal results_received
        if message.get('stage') == 'security':
            results_received += 1
            logger.info(f"Received security scan result {results_received}:")
            logger.info(json.dumps(message, indent=2))
    
    # Start listening for results
    consumer = KafkaClient.consume_messages_async(
        topic="agent.results",
        group_id=f"test-security-results-{int(time.time())}",
        message_handler=result_handler
    )
    
    try:
        # Wait for results or timeout
        while time.time() - start_time < timeout and results_received < 1:
            time.sleep(1)
            
        return results_received > 0
    finally:
        # Stop the consumer
        if consumer:
            consumer.stop()

if __name__ == "__main__":
    # Run all tests
    test_with_standard_image()
    test_with_vulnerable_image()
    test_with_local_image()
    
    # Listen for results
    listen_for_results()
