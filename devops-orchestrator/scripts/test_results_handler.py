#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test script for Phase 8 of the DevOps Pipeline Orchestrator.
This tests the results handling and notification functionality.
"""

import os
import sys
import time
import json
import uuid
import logging
import threading
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.kafka_client import KafkaClient
from orchestrator.results_handler import get_results_handler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_results_handler")

# Constants
RESULTS_TOPIC = "agent.results"


def generate_test_pipeline_id() -> str:
    """Generate a unique test pipeline ID."""
    return f"test-pipeline-{uuid.uuid4().hex[:8]}"


def send_test_result(pipeline_id: str, stage: str, success: bool) -> None:
    """
    Send a test result for a pipeline stage.
    
    Args:
        pipeline_id: The pipeline ID
        stage: The pipeline stage name
        success: Whether the stage was successful
    """
    # Create a result message
    message = {
        "pipeline_id": pipeline_id,
        "stage": stage,
        "success": success,
        "timestamp": time.time(),
        "results": {
            "success": success,
            "duration": 5.2,
            "details": f"Test {stage} result: {'SUCCESS' if success else 'FAILED'}"
        }
    }
    
    # If it's a build or security stage, add image info
    if stage in ["build", "security"]:
        message["image"] = {
            "name": "test-app",
            "tag": "latest"
        }
    
    # Send the message to Kafka
    logger.info(f"Sending test result for {pipeline_id}, stage: {stage}, success: {success}")
    KafkaClient.send_message(
        topic=RESULTS_TOPIC,
        message=message,
        key=pipeline_id
    )


def test_successful_pipeline():
    """Test a fully successful pipeline."""
    pipeline_id = generate_test_pipeline_id()
    logger.info(f"Starting test for successful pipeline: {pipeline_id}")
    
    # Send successful results for each stage
    stages = ["lint", "test", "build", "security"]
    for stage in stages:
        send_test_result(pipeline_id, stage, True)
        time.sleep(2)  # Wait between stages
    
    logger.info(f"Completed successful pipeline test: {pipeline_id}")
    return pipeline_id


def test_failing_pipeline():
    """Test a pipeline with failures."""
    pipeline_id = generate_test_pipeline_id()
    logger.info(f"Starting test for failing pipeline: {pipeline_id}")
    
    # First two stages succeed, third fails
    send_test_result(pipeline_id, "lint", True)
    time.sleep(2)
    
    send_test_result(pipeline_id, "test", True)
    time.sleep(2)
    
    # Send a failing result for build
    send_test_result(pipeline_id, "build", False)
    time.sleep(2)
    
    logger.info(f"Completed failing pipeline test: {pipeline_id}")
    return pipeline_id


def test_retry_pipeline():
    """Test a pipeline with retry behavior."""
    pipeline_id = generate_test_pipeline_id()
    logger.info(f"Starting test for retry pipeline: {pipeline_id}")
    
    # First stage succeeds
    send_test_result(pipeline_id, "lint", True)
    time.sleep(2)
    
    # Second stage fails initially
    send_test_result(pipeline_id, "test", False)
    time.sleep(10)  # Wait for retry to be scheduled
    
    # Second stage succeeds on retry
    send_test_result(pipeline_id, "test", True)
    time.sleep(2)
    
    # Remaining stages succeed
    send_test_result(pipeline_id, "build", True)
    time.sleep(2)
    
    send_test_result(pipeline_id, "security", True)
    time.sleep(2)
    
    logger.info(f"Completed retry pipeline test: {pipeline_id}")
    return pipeline_id


def listen_for_notifications():
    """
    Start a results handler to listen for notifications.
    This simulates the orchestrator's results handler.
    """
    logger.info("Starting results handler to listen for notifications")
    handler = get_results_handler()
    handler.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping results handler")
        handler.stop()


def main():
    """Main test function."""
    logger.info("Starting Phase 8 tests: Results Handling in Orchestrator")
    
    # Start a thread with the results handler
    handler_thread = threading.Thread(target=listen_for_notifications)
    handler_thread.daemon = True
    handler_thread.start()
    
    try:
        # Wait for handler to initialize
        time.sleep(3)
        
        # Run test scenarios
        successful_id = test_successful_pipeline()
        logger.info(f"Successful pipeline ID: {successful_id}")
        
        time.sleep(5)
        
        failing_id = test_failing_pipeline()
        logger.info(f"Failing pipeline ID: {failing_id}")
        
        time.sleep(5)
        
        retry_id = test_retry_pipeline()
        logger.info(f"Retry pipeline ID: {retry_id}")
        
        # Keep running to observe notifications
        logger.info("\nTests completed. Press Ctrl+C to exit.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Tests interrupted. Exiting.")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
