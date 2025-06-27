#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CLI tool to simulate GitHub webhook calls for testing the orchestrator.
"""

import os
import sys
import json
import argparse
import hmac
import hashlib
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv('config/.env')

# GitHub webhook secret
GITHUB_WEBHOOK_SECRET = os.getenv('GITHUB_WEBHOOK_SECRET', 'development_secret_only')


def generate_signature(payload):
    """Generate GitHub webhook signature."""
    payload_bytes = json.dumps(payload).encode('utf-8')
    signature = hmac.new(
        GITHUB_WEBHOOK_SECRET.encode('utf-8'),
        payload_bytes,
        hashlib.sha1
    ).hexdigest()
    return f"sha1={signature}"


def send_webhook(event_type, payload, webhook_url):
    """Send webhook to the orchestrator."""
    headers = {
        'Content-Type': 'application/json',
        'X-GitHub-Event': event_type,
        'X-Hub-Signature': generate_signature(payload)
    }
    
    response = requests.post(webhook_url, json=payload, headers=headers)
    
    print(f"Response Status Code: {response.status_code}")
    print("Response Body:")
    print(json.dumps(response.json(), indent=2))


def generate_push_event(repo, branch="main"):
    """Generate a push event payload."""
    return {
        "ref": f"refs/heads/{branch}",
        "repository": {
            "name": repo.split("/")[-1],
            "full_name": repo,
            "clone_url": f"https://github.com/{repo}.git",
            "html_url": f"https://github.com/{repo}"
        },
        "pusher": {
            "name": "test-user",
            "email": "test@example.com"
        },
        "sender": {
            "login": "test-user",
            "id": 12345
        }
    }


def generate_pull_request_event(repo, branch="feature-branch"):
    """Generate a pull request event payload."""
    repo_name = repo.split("/")[-1]
    return {
        "action": "opened",
        "number": 1,
        "pull_request": {
            "html_url": f"https://github.com/{repo}/pull/1",
            "title": "Test PR",
            "user": {
                "login": "test-user"
            },
            "body": "This is a test PR",
            "head": {
                "ref": branch,
                "sha": "abcdef123456",
                "repo": {
                    "name": repo_name,
                    "full_name": repo,
                    "clone_url": f"https://github.com/{repo}.git"
                }
            },
            "base": {
                "ref": "main",
                "sha": "123456abcdef",
                "repo": {
                    "name": repo_name,
                    "full_name": repo,
                    "clone_url": f"https://github.com/{repo}.git"
                }
            }
        },
        "repository": {
            "name": repo_name,
            "full_name": repo,
            "clone_url": f"https://github.com/{repo}.git",
            "html_url": f"https://github.com/{repo}"
        },
        "sender": {
            "login": "test-user",
            "id": 12345
        }
    }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Send test webhook event to orchestrator")
    parser.add_argument("--event", choices=["push", "pull_request"], default="push",
                        help="GitHub event type to simulate")
    parser.add_argument("--repo", default="test-org/test-repo",
                        help="Repository name (org/repo)")
    parser.add_argument("--branch", default="main",
                        help="Branch name")
    parser.add_argument("--url", default="http://localhost:8000/webhook",
                        help="Webhook URL")
    
    args = parser.parse_args()
    
    if args.event == "push":
        payload = generate_push_event(args.repo, args.branch)
    else:
        payload = generate_pull_request_event(args.repo, args.branch)
    
    print(f"Sending {args.event} event for {args.repo}:{args.branch} to {args.url}")
    send_webhook(args.event, payload, args.url)


if __name__ == "__main__":
    sys.exit(main())
