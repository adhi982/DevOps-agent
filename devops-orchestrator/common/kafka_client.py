#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import logging
import os
import threading
from typing import Any, Dict, Optional, Callable

from dotenv import load_dotenv
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Kafka configuration
KAFKA_HOST = os.getenv('KAFKA_HOST', 'localhost')
KAFKA_PORT = os.getenv('KAFKA_PORT', '9092')
KAFKA_BOOTSTRAP_SERVERS = f'{KAFKA_HOST}:{KAFKA_PORT}'

# Constants for configuration
KAFKA_CONNECT_TIMEOUT_MS = 30000     # 30 seconds timeout for connection
KAFKA_REQUEST_TIMEOUT_MS = 40000     # 40 seconds for request timeout

class KafkaClient:
    """
    A utility class for working with Kafka producers and consumers.
    Provides simplified interfaces for sending and receiving messages.
    """
    
    @staticmethod
    def get_producer() -> KafkaProducer:
        """
        Create a Kafka producer with JSON serialization.
        
        Returns:
            KafkaProducer: A configured Kafka producer instance
        """
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks='all',          # Wait for all replicas to acknowledge
                retries=5,           # Increased retry count
                retry_backoff_ms=500,# Backoff between retries
                linger_ms=5,         # Small delay to batch messages
                connections_max_idle_ms=540000,  # Longer idle connections (9 min)
                max_block_ms=30000,  # Max time to block on send
                request_timeout_ms=KAFKA_REQUEST_TIMEOUT_MS,
                # IPv4 only to prevent IPv6 issues on Windows
                api_version_auto_timeout_ms=KAFKA_CONNECT_TIMEOUT_MS,
                reconnect_backoff_ms=1000,       # 1 second backoff for reconnect
                reconnect_backoff_max_ms=10000   # 10 seconds max backoff
            )
            logger.info(f"Created Kafka producer connected to {KAFKA_BOOTSTRAP_SERVERS}")
            return producer
        except KafkaError as e:
            logger.error(f"Failed to create Kafka producer: {e}")
            raise

    @staticmethod
    def get_consumer(topic: str, group_id: str, auto_offset_reset: str = 'earliest') -> KafkaConsumer:
        """
        Create a Kafka consumer for a specific topic.
        
        Args:
            topic (str): The Kafka topic to consume from
            group_id (str): Consumer group ID
            auto_offset_reset (str): Where to start consuming from if no offset is stored
            
        Returns:
            KafkaConsumer: A configured Kafka consumer instance
        """
        try:
            # Try with IPv4 settings first
            for attempt in range(1, 4):  # Try up to 3 times
                try:
                    logger.info(f"Attempting to connect to Kafka (attempt {attempt}/3)...")
                    consumer = KafkaConsumer(
                        topic,
                        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                        group_id=group_id,
                        auto_offset_reset=auto_offset_reset,
                        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                        enable_auto_commit=True,
                        auto_commit_interval_ms=1000,  # Commit offset every second
                        session_timeout_ms=30000,  # 30 seconds session timeout
                        heartbeat_interval_ms=10000,  # 10 seconds heartbeat
                        consumer_timeout_ms=60000,  # 60 seconds consumer timeout
                        request_timeout_ms=KAFKA_REQUEST_TIMEOUT_MS,
                        connections_max_idle_ms=540000,  # 9 minutes idle
                        reconnect_backoff_ms=1000,  # 1 second backoff
                        reconnect_backoff_max_ms=10000,  # 10 seconds max backoff
                        api_version_auto_timeout_ms=KAFKA_CONNECT_TIMEOUT_MS
                    )
                    # Test the connection by polling once
                    consumer.poll(timeout_ms=5000)
                    break
                except KafkaError as e:
                    if attempt < 3:
                        logger.warning(f"Connection attempt {attempt} failed: {e}. Retrying...")
                        import time
                        time.sleep(2)
                    else:
                        raise
            logger.info(f"Created Kafka consumer for topic '{topic}' with group '{group_id}'")
            return consumer
        except KafkaError as e:
            logger.error(f"Failed to create Kafka consumer: {e}")
            raise

    @staticmethod
    def send_message(topic: str, message: Dict[str, Any], key: Optional[str] = None) -> None:
        """
        Send a message to a Kafka topic.
        
        Args:
            topic (str): The Kafka topic to send to
            message (Dict[str, Any]): The message to send
            key (Optional[str]): Optional message key for partitioning
        """
        producer = KafkaClient.get_producer()
        try:
            future = producer.send(
                topic, 
                value=message, 
                key=key.encode('utf-8') if key else None
            )
            record_metadata = future.get(timeout=10)
            logger.info(f"Message sent to topic={record_metadata.topic}, partition={record_metadata.partition}, offset={record_metadata.offset}")
        except Exception as e:
            logger.error(f"Error sending message to Kafka: {e}")
            raise
        finally:
            producer.flush()
            producer.close()

    @staticmethod
    def consume_messages(topic: str, group_id: str, message_handler: Callable[[Dict[str, Any]], None]) -> None:
        """
        Consume messages from a Kafka topic and process them with a handler function.
        
        Args:
            topic (str): The Kafka topic to consume from
            group_id (str): Consumer group ID
            message_handler (Callable): Function that processes each message
        """
        consumer = KafkaClient.get_consumer(topic, group_id)
        try:
            logger.info(f"Starting to consume messages from topic '{topic}'")
            for message in consumer:
                try:
                    logger.info(f"Received message: {message.value}")
                    message_handler(message.value)
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
        except KafkaError as e:
            logger.error(f"Kafka consumer error: {e}")
        finally:
            consumer.close()
            logger.info("Kafka consumer closed")

    @staticmethod
    def consume_messages_async(topic: str, group_id: str, message_handler: Callable[[Dict[str, Any]], None], 
                              auto_offset_reset: str = 'earliest'):
        """
        Asynchronously consume messages from Kafka topic and process them with the message handler.
        
        Args:
            topic (str): The Kafka topic to consume from
            group_id (str): Consumer group ID
            message_handler (Callable): Function to handle received messages
            auto_offset_reset (str): Where to start consuming from if no offset is stored
            
        Returns:
            AsyncConsumer: An object with a stop() method to stop consumption
        """
        return AsyncConsumer(topic, group_id, message_handler, auto_offset_reset)


class AsyncConsumer:
    """
    Helper class for asynchronous Kafka message consumption.
    """
    
    def __init__(self, topic: str, group_id: str, message_handler: Callable[[Dict[str, Any]], None], 
                auto_offset_reset: str = 'earliest'):
        """
        Initialize the async consumer.
        
        Args:
            topic (str): Kafka topic to consume from
            group_id (str): Consumer group ID
            message_handler (Callable): Function to process messages
            auto_offset_reset (str): Where to start consuming from
        """
        self.topic = topic
        self.group_id = group_id
        self.message_handler = message_handler
        self.auto_offset_reset = auto_offset_reset
        self.consumer = None
        self.running = False
        self.thread = None
        
        # Start consuming
        self.start()
        
    def start(self):
        """Start the consumer in a separate thread."""
        if self.running:
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._consume_loop)
        self.thread.daemon = True
        self.thread.start()
        logger.info(f"Started async consumer for topic {self.topic} with group {self.group_id}")
        
    def _consume_loop(self):
        """Background thread for message consumption."""
        try:
            # Get a consumer
            self.consumer = KafkaClient.get_consumer(
                topic=self.topic,
                group_id=self.group_id,
                auto_offset_reset=self.auto_offset_reset
            )
            
            # Consume messages until stopped
            while self.running:
                for message in self.consumer:
                    if not self.running:
                        break
                        
                    try:
                        self.message_handler(message.value)
                    except Exception as e:
                        logger.error(f"Error handling message in async consumer: {e}")
                        
        except Exception as e:
            if self.running:  # Only log if we didn't stop intentionally
                logger.error(f"Error in async consumer: {e}")
        finally:
            # Close the consumer when done
            if self.consumer:
                try:
                    self.consumer.close()
                except Exception as e:
                    logger.error(f"Error closing consumer: {e}")
                    
    def stop(self):
        """Stop the consumer and close the Kafka connection."""
        if not self.running:
            return
            
        logger.info(f"Stopping async consumer for topic {self.topic}")
        self.running = False
        
        # Wait for the thread to terminate
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5.0)
            
        # Force close the consumer if still open
        if self.consumer:
            try:
                self.consumer.close(autocommit=False)
            except Exception:
                pass
            
        logger.info(f"Async consumer for topic {self.topic} stopped")


# Simple usage examples
def send_to_kafka(topic: str, data: Dict[str, Any], key: Optional[str] = None) -> None:
    """Simple wrapper function to send a message to Kafka"""
    KafkaClient.send_message(topic, data, key)


def consume_from_kafka(topic: str, group_id: str, handler_func: Callable) -> None:
    """Simple wrapper function to consume messages from Kafka"""
    KafkaClient.consume_messages(topic, group_id, handler_func)
