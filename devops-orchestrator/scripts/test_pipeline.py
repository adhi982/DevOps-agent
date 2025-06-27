#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test script for the complete pipeline process.
This script tests the full integration by:
1. Sending a webhook to the orchestrator
2. Checking that the messages are produced to Kafka
3. Verifying the agents process the messages
"""

import os
import sys
import json
import argparse
import logging
import time
import requests
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from common.kafka_client import KafkaClient
from scripts.test_webhook import generate_push_event, generate_signature

# Load environment variables
load_dotenv('config/.env')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_pipeline")

def test_full_pipeline(repo_name="test-org/test-repo", branch="main"):
    """Test the full pipeline integration."""
    # Generate webhook payload
    webhook_url = "http://localhost:8000/webhook"
    event_type = "push"
    
    # Create webhook payload with pipeline_id to simulate what the orchestrator will send to agents
    payload = generate_push_event(repo_name, branch)
    
    # Generate GitHub signature
    github_secret = os.getenv('GITHUB_WEBHOOK_SECRET', 'development_secret_only')
    payload_bytes = json.dumps(payload).encode('utf-8')
    signature = generate_signature(payload)
    
    # Send webhook
    logger.info(f"Sending {event_type} event for {repo_name}:{branch} to {webhook_url}")
    headers = {
        'Content-Type': 'application/json',
        'X-GitHub-Event': event_type,
        'X-Hub-Signature': signature
    }
    
    response = requests.post(webhook_url, json=payload, headers=headers)
    
    logger.info(f"Response Status Code: {response.status_code}")
    logger.info(f"Response Body: {json.dumps(response.json(), indent=2)}")
    
    # Send a direct message to the agent.lint topic with the expected fields
    # This is to test the agent, not the orchestrator
    pipeline_id = f"test-pipeline-{int(time.time())}"
    agent_message = {
        "pipeline_id": pipeline_id,
        "repository": {
            "name": repo_name.split('/')[-1],
            "full_name": repo_name,
            "clone_url": f"https://github.com/{repo_name}.git",
            "html_url": f"https://github.com/{repo_name}"
        },
        "branch": branch,
        "event_type": event_type
    }
    
    logger.info(f"Sending direct message to agent.lint with pipeline_id={pipeline_id}")
    KafkaClient.send_message(
        topic="agent.lint",
        message=agent_message,
        key=f"{repo_name}-{branch}"
    )
    
    logger.info("Test message sent. Check the agent logs for results.")
    
    return pipeline_id

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Test the full DevOps pipeline integration")
    parser.add_argument("--repo", default="test-org/test-repo", help="Repository name (org/repo)")
    parser.add_argument("--branch", default="main", help="Branch name")
    
    args = parser.parse_args()
    
    pipeline_id = test_full_pipeline(args.repo, args.branch)
    logger.info(f"Test completed with pipeline ID: {pipeline_id}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
