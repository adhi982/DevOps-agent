"""
Pipeline manager module that handles the pipeline state and orchestrates the flow.
"""

import os
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

# Add project root to path to fix imports
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.kafka_client import KafkaClient
from orchestrator.config import ConfigLoader, PipelineConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PipelineStatus(str, Enum):
    """Enum for pipeline status values."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StageStatus(str, Enum):
    """Enum for stage status values."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class PipelineInstance:
    """
    Represents a running pipeline instance with its current state.
    """
    def __init__(
        self, 
        pipeline_id: str, 
        repo_name: str, 
        branch: str, 
        config: PipelineConfig
    ):
        self.pipeline_id = pipeline_id
        self.repo_name = repo_name
        self.branch = branch
        self.config = config
        self.status = PipelineStatus.PENDING
        self.start_time = datetime.now()
        self.end_time = None
        self.stages = {
            stage.name: {
                "status": StageStatus.PENDING,
                "start_time": None,
                "end_time": None,
                "results": None,
                "retries": 0
            }
            for stage in config.stages
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert pipeline instance to dictionary."""
        return {
            "pipeline_id": self.pipeline_id,
            "repo_name": self.repo_name,
            "branch": self.branch,
            "status": self.status,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "stages": self.stages
        }
    
    def update_stage_status(self, stage_name: str, status: StageStatus, results: Optional[Dict] = None):
        """Update the status of a stage."""
        if stage_name not in self.stages:
            logger.warning(f"Stage {stage_name} not found in pipeline {self.pipeline_id}")
            return
        
        self.stages[stage_name]["status"] = status
        
        if status == StageStatus.RUNNING:
            self.stages[stage_name]["start_time"] = datetime.now().isoformat()
        
        if status in [StageStatus.SUCCESS, StageStatus.FAILED, StageStatus.SKIPPED]:
            self.stages[stage_name]["end_time"] = datetime.now().isoformat()
        
        if results:
            self.stages[stage_name]["results"] = results
    
    def all_stages_completed(self) -> bool:
        """Check if all stages have completed."""
        return all(
            self.stages[stage]["status"] in [StageStatus.SUCCESS, StageStatus.FAILED, StageStatus.SKIPPED]
            for stage in self.stages
        )
    
    def update_pipeline_status(self):
        """Update overall pipeline status based on stages."""
        if any(self.stages[stage]["status"] == StageStatus.FAILED for stage in self.stages):
            self.status = PipelineStatus.FAILED
        elif all(self.stages[stage]["status"] == StageStatus.SUCCESS for stage in self.stages):
            self.status = PipelineStatus.SUCCESS
        elif any(self.stages[stage]["status"] == StageStatus.RUNNING for stage in self.stages):
            self.status = PipelineStatus.RUNNING
        elif any(self.stages[stage]["status"] == StageStatus.PENDING for stage in self.stages):
            self.status = PipelineStatus.PENDING
        
        if self.all_stages_completed():
            self.end_time = datetime.now()


class PipelineManager:
    """
    Manages the state and execution of pipelines.
    """
    def __init__(self):
        self.pipelines: Dict[str, PipelineInstance] = {}
        self.config_loader = ConfigLoader()
        
        # Load default pipeline configuration
        self.default_config = self.config_loader.load_pipeline_config()
    
    def generate_pipeline_id(self, repo: str, branch: str) -> str:
        """Generate a unique pipeline ID."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"{repo.replace('/', '-')}-{branch}-{timestamp}"
    
    def create_pipeline(self, repo_name: str, branch: str, event_data: Dict[str, Any]) -> PipelineInstance:
        """Create a new pipeline instance."""
        pipeline_id = self.generate_pipeline_id(repo_name, branch)
        
        # Use repository-specific config if available, otherwise use default
        repo_config_path = f"config/pipelines/{repo_name}.yml"
        if os.path.exists(repo_config_path):
            config = self.config_loader.load_pipeline_config(repo_config_path)
        else:
            config = self.default_config
        
        # Create pipeline instance
        pipeline = PipelineInstance(
            pipeline_id=pipeline_id,
            repo_name=repo_name,
            branch=branch,
            config=config
        )
        
        # Store pipeline
        self.pipelines[pipeline_id] = pipeline
        logger.info(f"Created pipeline {pipeline_id} for {repo_name}:{branch}")
        
        # Start the pipeline
        self.start_pipeline(pipeline_id, event_data)
        
        return pipeline
    
    def start_pipeline(self, pipeline_id: str, event_data: Dict[str, Any]):
        """Start pipeline execution."""
        if pipeline_id not in self.pipelines:
            logger.error(f"Pipeline {pipeline_id} not found")
            return
        
        pipeline = self.pipelines[pipeline_id]
        pipeline.status = PipelineStatus.RUNNING
        
        # Trigger initial stages (those without dependencies)
        config_stages = pipeline.config.get("stages", [])
        initial_stages = [
            stage["name"] for stage in config_stages 
            if not stage.get("dependencies")
        ]
        
        for stage_name in initial_stages:
            self.trigger_stage(pipeline_id, stage_name, event_data)
    
    def trigger_stage(self, pipeline_id: str, stage_name: str, event_data: Dict[str, Any]):
        """Trigger a specific pipeline stage."""
        if pipeline_id not in self.pipelines:
            logger.error(f"Pipeline {pipeline_id} not found")
            return
        
        pipeline = self.pipelines[pipeline_id]
        if stage_name not in pipeline.stages:
            logger.error(f"Stage {stage_name} not found in pipeline {pipeline_id}")
            return
        
        # Update stage status
        pipeline.update_stage_status(stage_name, StageStatus.RUNNING)
        
        # Create event payload for the agent
        event_payload = {
            "pipeline_id": pipeline_id,
            "repo_name": pipeline.repo_name,
            "branch": pipeline.branch,
            "stage": stage_name,
            "repository": event_data.get("repository", {}),
            "event_type": event_data.get("event_type", ""),
            "timestamp": datetime.now().isoformat()
        }
        
        # Send message to appropriate Kafka topic
        topic = f"agent.{stage_name}"
        try:
            KafkaClient.send_message(
                topic=topic,
                message=event_payload,
                key=f"{pipeline.repo_name}-{pipeline.branch}"
            )
            logger.info(f"Triggered stage {stage_name} for pipeline {pipeline_id}")
        except Exception as e:
            logger.error(f"Failed to trigger stage {stage_name}: {e}")
            pipeline.update_stage_status(stage_name, StageStatus.FAILED, {"error": str(e)})
            self.check_pipeline_progress(pipeline_id)
    
    def process_stage_result(self, pipeline_id: str, stage_name: str, result: Dict[str, Any]):
        """Process results from a completed stage."""
        if pipeline_id not in self.pipelines:
            logger.error(f"Pipeline {pipeline_id} not found")
            return
        
        pipeline = self.pipelines[pipeline_id]
        if stage_name not in pipeline.stages:
            logger.error(f"Stage {stage_name} not found in pipeline {pipeline_id}")
            return
        
        # Update stage with results
        status = StageStatus.SUCCESS if result.get("success", False) else StageStatus.FAILED
        pipeline.update_stage_status(stage_name, status, result)
        
        # Handle retries for failed stages
        if status == StageStatus.FAILED:
            stage_data = pipeline.stages[stage_name]
            stage_config = next(
                (s for s in pipeline.config.get("stages", []) if s["name"] == stage_name),
                {"retries": 0}
            )
            max_retries = stage_config.get("retries", 0)
            
            if stage_data["retries"] < max_retries:
                # Retry the stage
                stage_data["retries"] += 1
                logger.info(f"Retrying stage {stage_name} for pipeline {pipeline_id} (attempt {stage_data['retries']})")
                # Re-trigger the stage
                self.trigger_stage(pipeline_id, stage_name, {"repository": {"name": pipeline.repo_name}})
                return
        
        # Check overall pipeline progress
        self.check_pipeline_progress(pipeline_id)
    
    def check_pipeline_progress(self, pipeline_id: str):
        """Check pipeline progress and trigger next stages if needed."""
        if pipeline_id not in self.pipelines:
            logger.error(f"Pipeline {pipeline_id} not found")
            return
        
        pipeline = self.pipelines[pipeline_id]
        
        # Update overall pipeline status
        pipeline.update_pipeline_status()
        
        # If pipeline is finished, send notifications
        if pipeline.status in [PipelineStatus.SUCCESS, PipelineStatus.FAILED]:
            logger.info(f"Pipeline {pipeline_id} finished with status {pipeline.status}")
            self.send_pipeline_notification(pipeline_id)
            return
        
        # Find stages that can be started (all dependencies are complete)
        config_stages = pipeline.config.get("stages", [])
        
        for stage_config in config_stages:
            stage_name = stage_config.get("name")
            if not stage_name or pipeline.stages.get(stage_name, {}).get("status") != StageStatus.PENDING:
                continue
            
            # Check if dependencies are completed successfully
            dependencies = stage_config.get("dependencies", [])
            all_deps_success = True
            
            for dep in dependencies:
                dep_status = pipeline.stages.get(dep, {}).get("status")
                if dep_status != StageStatus.SUCCESS:
                    all_deps_success = False
                    break
            
            if all_deps_success:
                # All dependencies are successful, trigger this stage
                logger.info(f"Triggering stage {stage_name} for pipeline {pipeline_id}")
                self.trigger_stage(
                    pipeline_id, 
                    stage_name, 
                    {"repository": {"name": pipeline.repo_name}}
                )
    
    def send_pipeline_notification(self, pipeline_id: str):
        """Send notification about pipeline completion."""
        if pipeline_id not in self.pipelines:
            logger.error(f"Pipeline {pipeline_id} not found")
            return
        
        pipeline = self.pipelines[pipeline_id]
        
        # Check if notifications should be sent
        notification_config = pipeline.config.get("notifications", {})
        should_notify = (
            (pipeline.status == PipelineStatus.SUCCESS and notification_config.get("notify_on_success", True)) or
            (pipeline.status == PipelineStatus.FAILED and notification_config.get("notify_on_failure", True))
        )
        
        if not should_notify:
            return
        
        # Prepare notification message
        message = {
            "pipeline_id": pipeline_id,
            "repo_name": pipeline.repo_name,
            "branch": pipeline.branch,
            "status": pipeline.status,
            "duration": (pipeline.end_time - pipeline.start_time).total_seconds() if pipeline.end_time else None,
            "stages": {
                name: {
                    "status": data["status"],
                    "duration": (
                        (datetime.fromisoformat(data["end_time"]) - datetime.fromisoformat(data["start_time"])).total_seconds()
                        if data["end_time"] and data["start_time"] else None
                    )
                }
                for name, data in pipeline.stages.items()
            }
        }
        
        # Send to notification topic
        try:
            KafkaClient.send_message("notifications", message, key=pipeline_id)
            logger.info(f"Sent notification for pipeline {pipeline_id}")
        except Exception as e:
            logger.error(f"Failed to send notification for pipeline {pipeline_id}: {e}")
    
    def get_pipeline_status(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a pipeline."""
        if pipeline_id not in self.pipelines:
            return None
        
        return self.pipelines[pipeline_id].to_dict()
    
    def list_pipelines(self) -> List[Dict[str, Any]]:
        """List all pipelines."""
        return [self.pipelines[pipeline_id].to_dict() for pipeline_id in self.pipelines]
    
    async def start_result_consumer(self):
        """Start consumer for agent result messages."""
        def handle_result(message):
            try:
                pipeline_id = message.get("pipeline_id")
                stage = message.get("stage")
                
                if not pipeline_id or not stage:
                    logger.error("Received invalid result message")
                    return
                
                logger.info(f"Received result for pipeline {pipeline_id}, stage {stage}")
                self.process_stage_result(pipeline_id, stage, message)
            except Exception as e:
                logger.error(f"Error processing result message: {e}")
        
        # Start Kafka consumer in a separate thread
        KafkaClient.consume_messages("agent.results", "orchestrator", handle_result)


# Singleton instance
pipeline_manager = PipelineManager()

if __name__ == "__main__":
    # For testing only
    asyncio.run(pipeline_manager.start_result_consumer())
