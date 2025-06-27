"""
Main FastAPI application for the DevOps Orchestrator.
This module sets up the web server and webhook endpoints.
"""

import os
import json
import uuid
import logging
import hmac
import hashlib
from typing import Dict, Any, Optional

import yaml
from fastapi import FastAPI, Request, Response, Depends, Header, HTTPException, status
from pydantic import BaseModel
from dotenv import load_dotenv

# Add project root to path to fix imports
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.kafka_client import KafkaClient
from orchestrator.results_handler import get_results_handler, ResultsHandler

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("orchestrator.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="DevOps Pipeline Orchestrator",
    description="A webhook listener that orchestrates CI/CD pipelines using autonomous agents",
    version="1.0.0"
)

# Load configuration
GITHUB_WEBHOOK_SECRET = os.getenv('GITHUB_WEBHOOK_SECRET', 'development_secret_only')
PIPELINE_CONFIG_PATH = os.getenv('PIPELINE_CONFIG_PATH', 'config/pipeline.yml')


class PipelineEvent(BaseModel):
    """
    Model representing a pipeline event that will be sent to Kafka.
    """
    repository: Dict[str, Any]
    event_type: str
    payload: Dict[str, Any]


async def verify_signature(request: Request, x_hub_signature: str = Header(None)) -> bool:
    """
    Verify GitHub webhook signature to ensure requests are legitimate.
    
    Args:
        request: The incoming request
        x_hub_signature: GitHub signature header
        
    Returns:
        bool: True if signature is valid, False otherwise
    """
    if not GITHUB_WEBHOOK_SECRET or GITHUB_WEBHOOK_SECRET == 'development_secret_only':
        logger.warning("Using default webhook secret. This should be changed in production!")
        return True
        
    if not x_hub_signature:
        logger.warning("No signature provided")
        return False
        
    # Get raw body
    body = await request.body()
    
    # Generate signature
    expected_signature = hmac.new(
        GITHUB_WEBHOOK_SECRET.encode('utf-8'),
        body,
        hashlib.sha1
    ).hexdigest()
    
    # Compare signatures
    received_signature = x_hub_signature.split('=')[1]
    return hmac.compare_digest(expected_signature, received_signature)


def load_pipeline_config() -> Dict[str, Any]:
    """
    Load pipeline configuration from YAML file.
    
    Returns:
        Dict: Pipeline configuration
    """
    try:
        with open(PIPELINE_CONFIG_PATH, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load pipeline config: {e}")
        # Return default config if loading fails
        return {
            "pipeline": {
                "stages": ["lint", "test", "build", "security"],
                "retry_on_failure": True,
                "notify_on_success": True
            }
        }


@app.on_event("startup")
async def startup_event():
    """Runs when the FastAPI server starts up."""
    logger.info("Starting DevOps Pipeline Orchestrator")
    logger.info(f"Loading pipeline config from: {PIPELINE_CONFIG_PATH}")
    config = load_pipeline_config()
    logger.info(f"Pipeline stages: {config.get('pipeline', {}).get('stages', [])}")
    
    # Initialize and start the results handler
    try:
        results_handler = get_results_handler()
        results_handler.start()
        logger.info("Results handler started successfully")
    except Exception as e:
        logger.error(f"Failed to start results handler: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Runs when the FastAPI server shuts down."""
    logger.info("Shutting down DevOps Pipeline Orchestrator")
    
    # Stop the results handler
    try:
        results_handler = get_results_handler()
        results_handler.stop()
        logger.info("Results handler stopped successfully")
    except Exception as e:
        logger.error(f"Error stopping results handler: {e}")


@app.get("/")
async def root():
    """Root endpoint for health checks and basic information."""
    return {
        "name": "DevOps Pipeline Orchestrator",
        "status": "running",
        "endpoints": {
            "/webhook": "GitHub webhook receiver",
            "/health": "Health check endpoint"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy"}


@app.get("/pipeline/{pipeline_id}")
async def get_pipeline_status(pipeline_id: str):
    """
    Get the current status of a pipeline.
    
    Args:
        pipeline_id: The unique identifier of the pipeline
        
    Returns:
        Dict: Current pipeline status
    """
    try:
        results_handler = get_results_handler()
        status = results_handler.results_tracker.get_pipeline_status(pipeline_id)
        return status
    except Exception as e:
        logger.error(f"Error retrieving pipeline status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve pipeline status: {str(e)}"
        )


@app.post("/webhook")
async def github_webhook(request: Request, response: Response):
    """
    GitHub webhook endpoint that receives events and triggers pipeline stages.
    
    Args:
        request: The incoming request containing GitHub event
        response: The response object
    
    Returns:
        Dict: Result of the webhook processing
    """
    # Verify GitHub webhook signature in production
    if not await verify_signature(request):
        logger.warning("Invalid webhook signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature"
        )
    
    # Get event type from headers
    event_type = request.headers.get("X-GitHub-Event", "push")
    logger.info(f"Received GitHub webhook event: {event_type}")
    
    # Parse payload
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload format"
        )
    
    # Only process certain events
    if event_type not in ["push", "pull_request"]:
        logger.info(f"Ignoring event type: {event_type}")
        return {"status": "ignored", "event_type": event_type}
    
    # Extract repository info
    try:
        repository = payload.get("repository", {})
        if not repository:
            raise ValueError("No repository information in payload")
        
        repo_name = repository.get("full_name", "unknown")
        repo_url = repository.get("clone_url", "")
        branch = "main"  # Default
        
        # Extract branch information
        if event_type == "push":
            branch = payload.get("ref", "").replace("refs/heads/", "")
        elif event_type == "pull_request":
            branch = payload.get("pull_request", {}).get("head", {}).get("ref", "")
        
        logger.info(f"Processing event for {repo_name}, branch: {branch}")
    except Exception as e:
        logger.error(f"Failed to extract repository info: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not process repository information"
        )
    
    # Load pipeline configuration
    config = load_pipeline_config()
    stages = config.get("pipeline", {}).get("stages", [])
    
    # Generate a unique pipeline ID
    pipeline_id = f"pipeline-{uuid.uuid4().hex[:8]}"
    
    # Create an event object to send to Kafka
    event = PipelineEvent(
        repository=repository,
        event_type=event_type,
        payload={
            "repository": repository,
            "branch": branch,
            "sender": payload.get("sender", {}),
            "event_type": event_type,
            # Include more context as needed
        }
    )
    
    # Add pipeline_id to the dictionary representation
    event_dict = event.dict()
    event_dict["pipeline_id"] = pipeline_id
    
    # Send event to each agent via Kafka
    try:
        for stage in stages:
            # Create topic name using the agent prefix and stage name
            stage_name = stage['name'] if isinstance(stage, dict) else stage
            topic = f"agent.{stage_name}"
            logger.info(f"Sending event to {topic}")
            
            # Send message to Kafka
            KafkaClient.send_message(
                topic=topic,
                message=event_dict,  # Use the dict with pipeline_id
                key=f"{repo_name}-{branch}"  # Use repo+branch as key for message ordering
            )
        
        # Log success
        logger.info(f"Successfully triggered pipeline {pipeline_id} for {repo_name}, branch: {branch}")
        return {
            "status": "success",
            "message": f"Pipeline triggered for {repo_name}",
            "pipeline_id": pipeline_id,
            "stages": stages
        }
    except Exception as e:
        logger.error(f"Failed to send events to Kafka: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger pipeline: {str(e)}"
        )


if __name__ == "__main__":
    # For development only - in production use uvicorn command
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
