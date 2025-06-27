#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test script for Slack notifications.
This script sends a test message to Slack to verify webhook integration.
"""

import os
import sys
import json
import argparse
import logging
from typing import Dict, Any

import requests
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from orchestrator.results_handler import SlackNotifier

# Load environment variables
load_dotenv('config/.env')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("slack_test")

# Get webhook URL from environment
SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL', '')


def send_direct_message(message: str) -> bool:
    """
    Send a simple message directly to Slack using the webhook URL.
    
    Args:
        message: The message to send
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not SLACK_WEBHOOK_URL:
        logger.error("SLACK_WEBHOOK_URL environment variable is not set")
        return False
    
    payload = {"text": message}
    
    try:
        response = requests.post(
            SLACK_WEBHOOK_URL,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        logger.info(f"Message sent successfully. Status code: {response.status_code}")
        return True
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        return False


def send_rich_message() -> bool:
    """
    Send a rich formatted message to Slack.
    
    Returns:
        bool: True if successful, False otherwise
    """
    if not SLACK_WEBHOOK_URL:
        logger.error("SLACK_WEBHOOK_URL environment variable is not set")
        return False
    
    # Create a rich message with blocks
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*DevOps Pipeline Status Update*"
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": "*Pipeline ID:*\ntest-pipeline-123"
                },
                {
                    "type": "mrkdwn",
                    "text": "*Status:*\nSUCCESS"
                }
            ]
        },
        {
            "type": "divider"
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "✅ *lint*: success\n✅ *test*: success\n✅ *build*: success\n✅ *security*: success"
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "Completed at: 2025-06-27 13:00:00 UTC"
                }
            ]
        }
    ]
    
    payload = {
        "text": "Pipeline test-pipeline-123 completed successfully",
        "blocks": blocks
    }
    
    try:
        response = requests.post(
            SLACK_WEBHOOK_URL,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        logger.info(f"Rich message sent successfully. Status code: {response.status_code}")
        return True
    except Exception as e:
        logger.error(f"Failed to send rich message: {e}")
        return False


def test_notifier() -> bool:
    """
    Test the SlackNotifier class from results_handler.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        notifier = SlackNotifier()
        
        # Test simple notification
        simple_result = notifier.send_notification("Test notification from SlackNotifier")
        
        # Test pipeline status notification
        status = {
            "pipeline_id": "test-notifier-pipeline",
            "status": "success",
            "stages": {
                "lint": {"status": "success", "retries": 0, "timestamp": "2025-06-27T13:00:00"},
                "test": {"status": "success", "retries": 1, "timestamp": "2025-06-27T13:05:00"},
                "build": {"status": "success", "retries": 0, "timestamp": "2025-06-27T13:10:00"},
                "security": {"status": "success", "retries": 0, "timestamp": "2025-06-27T13:15:00"}
            },
            "timestamp": "2025-06-27T13:15:00"
        }
        
        rich_result = notifier.notify_pipeline_status(status)
        
        return simple_result and rich_result
    except Exception as e:
        logger.error(f"Error testing notifier: {e}")
        return False


def main():
    """Main function to run the tests."""
    parser = argparse.ArgumentParser(description="Test Slack notification integration")
    parser.add_argument("--method", choices=["direct", "rich", "notifier"], default="notifier",
                      help="Which method to use for sending the test message")
    parser.add_argument("--message", default="Test message from DevOps Pipeline Orchestrator",
                      help="Message to send (for direct method only)")
    args = parser.parse_args()
    
    if not SLACK_WEBHOOK_URL:
        logger.error("SLACK_WEBHOOK_URL is not set in the environment or .env file.")
        logger.error("Please set it in config/.env or export it as an environment variable.")
        return 1
    
    logger.info(f"Testing Slack notifications using method: {args.method}")
    
    if args.method == "direct":
        result = send_direct_message(args.message)
    elif args.method == "rich":
        result = send_rich_message()
    else:  # notifier
        result = test_notifier()
    
    if result:
        logger.info("Slack notification test completed successfully!")
        return 0
    else:
        logger.error("Slack notification test failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
