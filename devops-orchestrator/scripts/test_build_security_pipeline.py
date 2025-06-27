#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
End-to-end test script for testing the complete pipeline.
This tests the sequence: Build -> Security scan
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
logger = logging.getLogger("test_pipeline")

def generate_pipeline_id():
    """Generate a unique pipeline ID with timestamp and random number."""
    timestamp = int(time.time())
    random_part = random.randint(1000, 9999)
    return f"pipeline-{timestamp}-{random_part}"

def test_build_and_security_pipeline():
    """Test the build and security scan pipeline."""
    pipeline_id = generate_pipeline_id()
    logger.info(f"Starting test pipeline with ID: {pipeline_id}")
    
    # First, trigger a build with a public Docker repository
    build_message = {
        "pipeline_id": pipeline_id,
        "repository": {
            "clone_url": "https://github.com/docker/getting-started",
            "name": "docker-getting-started"
        },
        "branch": "master",
        "event_type": "push",
        "docker": {
            "image_name": "pipeline-test-image",
            "tag": "latest",
            "dockerfile": "app/Dockerfile",
            "push": False
        }
    }
    
    # Send to build agent
    try:
        KafkaClient.send_message(
            topic="agent.build",
            message=build_message,
            key=pipeline_id
        )
        logger.info(f"Sent build message to Kafka for pipeline: {pipeline_id}")
    except Exception as e:
        logger.error(f"Failed to send build message: {e}")
        return False
    
    # Wait for build results (up to 5 minutes)
    build_results = wait_for_stage_results(pipeline_id, "build", 300)
    
    if not build_results or not build_results.get('success', False):
        logger.error(f"Build stage failed or timed out for pipeline: {pipeline_id}")
        return False
    
    logger.info(f"Build stage completed successfully for pipeline: {pipeline_id}")
    
    # Extract image info from build results
    image_name = build_results.get('results', {}).get('image_name', 'pipeline-test-image')
    image_tag = build_results.get('results', {}).get('image_tag', 'latest')
    
    # Now, trigger a security scan
    security_message = {
        "pipeline_id": pipeline_id,
        "image": {
            "name": image_name,
            "tag": image_tag
        },
        "scan_options": {
            "severity": "CRITICAL,HIGH",
            "timeout": 300,
            "format": "json"
        }
    }
    
    # Send to security agent
    try:
        KafkaClient.send_message(
            topic="agent.security",
            message=security_message,
            key=pipeline_id
        )
        logger.info(f"Sent security scan message to Kafka for pipeline: {pipeline_id}")
    except Exception as e:
        logger.error(f"Failed to send security message: {e}")
        return False
    
    # Wait for security results (up to 5 minutes)
    security_results = wait_for_stage_results(pipeline_id, "security", 300)
    
    if not security_results:
        logger.error(f"Security scan stage timed out for pipeline: {pipeline_id}")
        return False
    
    # Security scan might find vulnerabilities but still complete successfully
    success = security_results.get('success', False)
    vulnerabilities_found = security_results.get('results', {}).get('vulnerabilities_found', False)
    vulnerability_count = security_results.get('results', {}).get('vulnerability_count', 0)
    
    if success:
        logger.info(f"Security scan completed successfully for pipeline: {pipeline_id}")
        if vulnerabilities_found:
            logger.warning(f"Found {vulnerability_count} vulnerabilities in image {image_name}:{image_tag}")
        else:
            logger.info(f"No vulnerabilities found in image {image_name}:{image_tag}")
    else:
        logger.error(f"Security scan failed for pipeline: {pipeline_id}")
    
    return success

def wait_for_stage_results(pipeline_id, stage, timeout=300):
    """
    Wait for results for a specific pipeline stage.
    
    Args:
        pipeline_id: The pipeline ID to match
        stage: The stage name ('build', 'security', etc.)
        timeout: Maximum time to wait in seconds
        
    Returns:
        The results message or None if timed out
    """
    logger.info(f"Waiting for {stage} results for pipeline {pipeline_id} (timeout: {timeout}s)")
    
    start_time = time.time()
    results = []
    
    def result_handler(message):
        if (message.get('pipeline_id') == pipeline_id and 
            message.get('stage') == stage):
            results.append(message)
    
    # Start listening for results
    consumer = KafkaClient.consume_messages_async(
        topic="agent.results",
        group_id=f"test-pipeline-{int(time.time())}",
        message_handler=result_handler
    )
    
    try:
        # Wait for results or timeout
        while time.time() - start_time < timeout and not results:
            time.sleep(1)
            
        if results:
            result = results[0]
            logger.info(f"Received {stage} results for pipeline {pipeline_id}")
            return result
        else:
            logger.warning(f"Timeout waiting for {stage} results for pipeline {pipeline_id}")
            return None
    finally:
        # Stop the consumer
        if consumer:
            consumer.stop()

if __name__ == "__main__":
    success = test_build_and_security_pipeline()
    if success:
        logger.info("End-to-end test pipeline completed successfully!")
        sys.exit(0)
    else:
        logger.error("End-to-end test pipeline failed!")
        sys.exit(1)
