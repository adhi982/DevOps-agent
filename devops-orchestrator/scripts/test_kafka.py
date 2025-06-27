#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import time
import threading
import os
import sys

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Now we can import from common package
from common.kafka_client import send_to_kafka, consume_from_kafka

def handle_message(message):
    """Simple handler function for received messages"""
    print(f"Received message: {message}")
    print(f"Message type: {message.get('type')}")
    print(f"Message data: {message.get('data')}")
    print("-" * 50)

def start_consumer():
    """Start Kafka consumer in a separate thread"""
    print("Starting Kafka consumer...")
    consume_from_kafka(
        topic='agent.test',
        group_id='test-consumer',
        handler_func=handle_message
    )

def main():
    """Main function to test Kafka"""
    print("\n=== Kafka Connection Test ===\n")
    
    # First check if Kafka is available
    print("Step 1: Checking Kafka connectivity...")
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect(("localhost", 9092))
        s.close()
        print("✓ Successfully connected to Kafka broker at localhost:9092")
    except Exception as e:
        print(f"✗ Could not connect to Kafka: {e}")
        print("Please ensure Kafka is running with 'docker-compose up -d'")
        sys.exit(1)
        
    # Start consumer in a separate thread
    print("\nStep 2: Starting Kafka consumer...")
    consumer_thread = threading.Thread(target=start_consumer, daemon=True)
    consumer_thread.start()
    
    # Wait a bit for consumer to start
    time.sleep(5)
    
    # Send test messages
    print("\nStep 3: Sending test messages to Kafka...")
    for i in range(3):
        message = {
            'type': 'test',
            'data': {
                'id': i,
                'message': f'Test message {i}',
                'timestamp': time.time()
            }
        }
        send_to_kafka('agent.test', message)
        print(f"Sent message {i}")
        time.sleep(1)
    
    # Keep main thread alive to receive messages
    print("Waiting for messages to be consumed...")
    time.sleep(5)
    print("Test completed!")

if __name__ == "__main__":
    main()
