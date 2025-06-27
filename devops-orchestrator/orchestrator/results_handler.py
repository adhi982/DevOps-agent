#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Results Handler Module for DevOps Orchestrator

This module:
1. Listens to the 'agent.results' Kafka topic
2. Processes results from various agents (lint, test, build, security)
3. Implements retry logic for failed stages
4. Sends notifications (e.g., to Slack) based on results
"""

import os
import json
import time
import logging
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime

import requests
from dotenv import load_dotenv

# Import from project
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from common.kafka_client import KafkaClient

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("orchestrator_results.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("results_handler")

# Configuration from environment variables
SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL', '')
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
RETRY_DELAY_SECONDS = int(os.getenv('RETRY_DELAY_SECONDS', '60'))


class ResultsTracker:
    """
    Tracks the results of pipeline stages and manages retry attempts.
    """
    def __init__(self):
        # Dictionary to track pipeline results by pipeline ID
        # Format: {pipeline_id: {stage: {status, results, retries, timestamp}}}
        self.pipelines = {}
        
        # Lock for thread-safe access
        self.lock = threading.RLock()
    
    def record_result(self, pipeline_id: str, stage: str, success: bool, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Record the result of a pipeline stage.
        
        Args:
            pipeline_id (str): The unique identifier for the pipeline
            stage (str): The pipeline stage (lint, test, build, security, etc.)
            success (bool): Whether the stage was successful
            results (Dict[str, Any]): Detailed results data
            
        Returns:
            Dict: Updated pipeline status
        """
        with self.lock:
            # Create pipeline entry if it doesn't exist
            if pipeline_id not in self.pipelines:
                self.pipelines[pipeline_id] = {}
            
            # Record the result
            stage_status = {
                'status': 'success' if success else 'failed',
                'results': results,
                'retries': self.pipelines.get(pipeline_id, {}).get(stage, {}).get('retries', 0),
                'timestamp': datetime.now().isoformat()
            }
            
            # Update in pipelines dictionary
            self.pipelines[pipeline_id][stage] = stage_status
            
            # Return a copy of the current pipeline status
            return self._get_pipeline_status(pipeline_id)
    
    def should_retry(self, pipeline_id: str, stage: str) -> bool:
        """
        Determine if a failed stage should be retried.
        
        Args:
            pipeline_id (str): The unique identifier for the pipeline
            stage (str): The pipeline stage (lint, test, build, security, etc.)
            
        Returns:
            bool: True if the stage should be retried, False otherwise
        """
        with self.lock:
            # Check if pipeline and stage exist
            if pipeline_id not in self.pipelines or stage not in self.pipelines[pipeline_id]:
                return False
            
            stage_info = self.pipelines[pipeline_id][stage]
            
            # Only retry failures
            if stage_info['status'] == 'success':
                return False
            
            # Check retry count
            return stage_info['retries'] < MAX_RETRIES
    
    def increment_retry_count(self, pipeline_id: str, stage: str) -> int:
        """
        Increment the retry count for a stage.
        
        Args:
            pipeline_id (str): The unique identifier for the pipeline
            stage (str): The pipeline stage to retry
            
        Returns:
            int: New retry count
        """
        with self.lock:
            if pipeline_id not in self.pipelines or stage not in self.pipelines[pipeline_id]:
                return 0
            
            current_retries = self.pipelines[pipeline_id][stage].get('retries', 0)
            new_retries = current_retries + 1
            
            # Update retry count
            self.pipelines[pipeline_id][stage]['retries'] = new_retries
            return new_retries
    
    def get_pipeline_status(self, pipeline_id: str) -> Dict[str, Any]:
        """
        Get the current status of a pipeline.
        
        Args:
            pipeline_id (str): The unique identifier for the pipeline
            
        Returns:
            Dict: Current pipeline status
        """
        with self.lock:
            return self._get_pipeline_status(pipeline_id)
    
    def _get_pipeline_status(self, pipeline_id: str) -> Dict[str, Any]:
        """
        Internal method to get pipeline status without locking.
        
        Args:
            pipeline_id (str): The unique identifier for the pipeline
            
        Returns:
            Dict: Current pipeline status
        """
        if pipeline_id not in self.pipelines:
            return {'pipeline_id': pipeline_id, 'status': 'unknown', 'stages': {}}
        
        # Determine overall status
        stages = self.pipelines[pipeline_id]
        all_success = all(info['status'] == 'success' for info in stages.values())
        any_failed = any(
            info['status'] == 'failed' and info['retries'] >= MAX_RETRIES 
            for info in stages.values()
        )
        
        status = 'success' if all_success else 'failed' if any_failed else 'in_progress'
        
        # Return formatted status
        return {
            'pipeline_id': pipeline_id,
            'status': status,
            'stages': {stage: {
                'status': info['status'],
                'retries': info['retries'],
                'timestamp': info['timestamp']
            } for stage, info in stages.items()},
            'timestamp': datetime.now().isoformat()
        }
    
    def cleanup_old_pipelines(self, max_age_hours: int = 24) -> int:
        """
        Remove pipelines older than specified hours.
        
        Args:
            max_age_hours (int): Maximum age in hours
            
        Returns:
            int: Number of pipelines removed
        """
        with self.lock:
            now = datetime.now()
            to_remove = []
            
            for pipeline_id, stages in self.pipelines.items():
                # Check if any stage timestamp is recent
                timestamps = [
                    datetime.fromisoformat(info['timestamp']) 
                    for info in stages.values() 
                    if 'timestamp' in info
                ]
                
                if not timestamps:
                    continue
                
                latest_timestamp = max(timestamps)
                age_hours = (now - latest_timestamp).total_seconds() / 3600
                
                if age_hours > max_age_hours:
                    to_remove.append(pipeline_id)
            
            # Remove old pipelines
            for pipeline_id in to_remove:
                del self.pipelines[pipeline_id]
                
            return len(to_remove)


class SlackNotifier:
    """
    Sends notifications to Slack about pipeline events.
    """
    def __init__(self, webhook_url: str = None):
        """
        Initialize with optional webhook URL. If not provided, use environment variable.
        
        Args:
            webhook_url (str, optional): Slack webhook URL
        """
        self.webhook_url = webhook_url or SLACK_WEBHOOK_URL
        
    def send_notification(self, message: str, blocks: List[Dict[str, Any]] = None) -> bool:
        """
        Send a notification to Slack.
        
        Args:
            message (str): The message text
            blocks (List[Dict], optional): Slack block elements for rich formatting
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.webhook_url:
            logger.warning("No Slack webhook URL configured. Skipping notification.")
            return False
            
        payload = {'text': message}
        if blocks:
            payload['blocks'] = blocks
            
        try:
            response = requests.post(
                self.webhook_url,
                data=json.dumps(payload),
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
            logger.info(f"Slack notification sent successfully: {message[:50]}...")
            return True
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False
    
    def notify_pipeline_status(self, status: Dict[str, Any]) -> bool:
        """
        Send a formatted notification about pipeline status.
        
        Args:
            status (Dict): Pipeline status as returned by ResultsTracker
            
        Returns:
            bool: True if successful, False otherwise
        """
        pipeline_id = status['pipeline_id']
        overall_status = status['status']
        stages = status['stages']
        
        # Create emoji for status
        emoji = "✅" if overall_status == "success" else "❌" if overall_status == "failed" else "🔄"
        
        # Create main message
        message = f"{emoji} Pipeline {pipeline_id} status: {overall_status.upper()}"
        
        # Create rich blocks for Slack
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{emoji} Pipeline Status Update*\n*ID:* {pipeline_id}\n*Status:* {overall_status.upper()}"
                }
            },
            {
                "type": "divider"
            }
        ]
        
        # Add stage details
        stage_details = []
        for stage, info in stages.items():
            stage_emoji = "✅" if info['status'] == "success" else "❌" if info['status'] == "failed" else "🔄"
            retry_info = f" (Retries: {info['retries']})" if info['retries'] > 0 else ""
            stage_details.append(f"{stage_emoji} *{stage}*: {info['status']}{retry_info}")
        
        if stage_details:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "\n".join(stage_details)
                }
            })
        
        return self.send_notification(message, blocks)


class ResultsHandler:
    """
    Main handler for agent results.
    Listens to Kafka, tracks results, manages retries, and sends notifications.
    """
    def __init__(self):
        self.results_tracker = ResultsTracker()
        self.slack_notifier = SlackNotifier()
        self.consumer = None
        self.running = False
    
    def start(self):
        """Start listening for results."""
        if self.running:
            return
            
        self.running = True
        
        # Start background cleanup thread
        self._start_cleanup_thread()
        
        # Start consuming results
        logger.info("Starting to listen for agent results...")
        try:
            self.consumer = KafkaClient.consume_messages_async(
                topic="agent.results",
                group_id="orchestrator-results-handler",
                message_handler=self._handle_result,
                auto_offset_reset="latest"  # Only process new messages
            )
        except Exception as e:
            logger.error(f"Failed to start results handler: {e}")
            self.running = False
            raise
    
    def stop(self):
        """Stop listening for results."""
        if not self.running:
            return
            
        logger.info("Stopping results handler...")
        self.running = False
        
        if self.consumer:
            self.consumer.stop()
            self.consumer = None
        
        logger.info("Results handler stopped.")
    
    def _handle_result(self, message: Dict[str, Any]):
        """
        Process a result message from an agent.
        
        Args:
            message: The result message from Kafka
        """
        try:
            # Extract key fields
            pipeline_id = message.get('pipeline_id')
            stage = message.get('stage')
            success = message.get('success', False)
            results = message.get('results', {})
            
            if not pipeline_id or not stage:
                logger.warning(f"Received invalid result message: missing pipeline_id or stage: {message}")
                return
            
            logger.info(f"Processing result for pipeline {pipeline_id}, stage {stage}, success={success}")
            
            # Record the result
            status = self.results_tracker.record_result(
                pipeline_id=pipeline_id,
                stage=stage,
                success=success,
                results=results
            )
            
            # Check if we need to retry
            if not success and self.results_tracker.should_retry(pipeline_id, stage):
                self._schedule_retry(pipeline_id, stage, message)
            
            # Send notification about stage completion
            self._send_stage_notification(pipeline_id, stage, success, status)
            
            # If pipeline is complete, send overall notification
            if status['status'] in ['success', 'failed']:
                self._send_pipeline_notification(status)
                
        except Exception as e:
            logger.error(f"Error processing result message: {e}", exc_info=True)
    
    def _schedule_retry(self, pipeline_id: str, stage: str, original_message: Dict[str, Any]):
        """
        Schedule a retry for a failed stage.
        
        Args:
            pipeline_id (str): The pipeline ID
            stage (str): The stage to retry
            original_message (Dict): The original message to be retried
        """
        # Increment retry count
        retry_count = self.results_tracker.increment_retry_count(pipeline_id, stage)
        logger.info(f"Scheduling retry #{retry_count} for pipeline {pipeline_id}, stage {stage}")
        
        # Modify message to include retry information
        retry_message = original_message.copy()
        if 'retries' not in retry_message:
            retry_message['retries'] = 0
        retry_message['retries'] = retry_count
        retry_message['retry_timestamp'] = datetime.now().isoformat()
        
        # Schedule the retry
        def retry_task():
            try:
                logger.info(f"Executing retry #{retry_count} for pipeline {pipeline_id}, stage {stage}")
                topic = f"agent.{stage}"
                KafkaClient.send_message(
                    topic=topic,
                    message=retry_message,
                    key=pipeline_id
                )
                logger.info(f"Retry message sent to {topic}")
            except Exception as e:
                logger.error(f"Failed to send retry message: {e}", exc_info=True)
        
        # Execute retry after delay
        threading.Timer(RETRY_DELAY_SECONDS, retry_task).start()
        logger.info(f"Retry scheduled in {RETRY_DELAY_SECONDS} seconds")
    
    def _send_stage_notification(self, pipeline_id: str, stage: str, success: bool, status: Dict[str, Any]):
        """
        Send notification about stage completion.
        
        Args:
            pipeline_id (str): The pipeline ID
            stage (str): The completed stage
            success (bool): Whether the stage was successful
            status (Dict): Current pipeline status
        """
        stage_info = status['stages'].get(stage, {})
        retry_info = f" (Retry {stage_info.get('retries', 0)})" if stage_info.get('retries', 0) > 0 else ""
        
        emoji = "✅" if success else "❌"
        message = f"{emoji} Pipeline {pipeline_id}: {stage} stage {('completed successfully' if success else 'failed')}{retry_info}."
        
        self.slack_notifier.send_notification(message)
    
    def _send_pipeline_notification(self, status: Dict[str, Any]):
        """
        Send notification about overall pipeline status.
        
        Args:
            status (Dict): Current pipeline status
        """
        self.slack_notifier.notify_pipeline_status(status)
    
    def _start_cleanup_thread(self):
        """Start background thread to clean up old pipeline data."""
        def cleanup_task():
            while self.running:
                try:
                    removed = self.results_tracker.cleanup_old_pipelines(max_age_hours=24)
                    if removed > 0:
                        logger.info(f"Cleaned up {removed} old pipelines")
                except Exception as e:
                    logger.error(f"Error in cleanup task: {e}")
                
                # Sleep for 1 hour before next cleanup
                for _ in range(60):  # Check running status every minute
                    if not self.running:
                        break
                    time.sleep(60)
        
        thread = threading.Thread(target=cleanup_task)
        thread.daemon = True
        thread.start()


# Singleton instance
_results_handler = None

def get_results_handler():
    """Get the singleton results handler instance."""
    global _results_handler
    if _results_handler is None:
        _results_handler = ResultsHandler()
    return _results_handler


if __name__ == "__main__":
    # For standalone testing
    handler = get_results_handler()
    handler.start()
    
    try:
        logger.info("Results handler running. Press Ctrl+C to exit.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down results handler.")
        handler.stop()
