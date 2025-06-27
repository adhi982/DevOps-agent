# Multi-Agent DevOps Pipeline Orchestrator

An event-driven CI/CD pipeline orchestrator with autonomous agents.

## Setup

1. Create a virtual environment:  
   ```
   python -m venv venv
   .\venv\Scripts\Activate
   ```

2. Install dependencies: pip install -r requirements.txt

3. Start Kafka: docker-compose up -d

4. Configure the environment: Edit config/.env with your settings

5. Run the orchestrator: uvicorn orchestrator.main:app --reload

6. Start the agents:
   ```
   python agents/lint_agent/main.py
   python agents/test_agent/main.py
   python agents/build_agent/main.py
   python agents/security_agent/main.py
   ```

## Architecture

- **Orchestrator**: Central controller that manages the pipeline
- **Agents**: Autonomous services handling specific tasks (lint, test, build, security)
- **Kafka**: Event bus for agent communication
- **GitHub Integration**: Webhook-based trigger for pipelines
- **Slack Notifications**: Real-time updates on pipeline progress

## Agents

### Lint Agent
Performs static code analysis on the source code using tools like Pylint.

### Test Agent
Runs automated tests on the codebase using pytest.

### Build Agent
Builds Docker images from the source code repository.

### Security Agent
Scans Docker images for vulnerabilities using Trivy. The security agent:
- Automatically downloads and installs Trivy if not present
- Scans Docker images for security vulnerabilities
- Provides vulnerability counts and severity information
- Reports results back to the orchestrator

## Pipeline Results and Notifications

The orchestrator includes a results handling system that:

1. Listens to the `agent.results` Kafka topic to collect output from all agents
2. Tracks the status of each pipeline stage
3. Implements retry logic for failed stages
4. Sends notifications to Slack for important events
5. Provides an API endpoint to query pipeline status

### Configuring Slack Notifications

1. Create a Slack App and Webhook URL:
   - Visit https://api.slack.com/apps
   - Create a new app and enable "Incoming Webhooks"
   - Create a webhook URL for your workspace and channel
   
2. Add the webhook URL to your environment:
   - Add `SLACK_WEBHOOK_URL=your_webhook_url` to `config/.env`

3. Configure notification settings:
   - Edit `config/notifications.yml` to customize retry behavior and notification preferences

4. Test Slack integration:
   ```
   python scripts/test_slack_notification.py
   ```

### Retry Mechanism

Failed pipeline stages are automatically retried based on configuration:
- `MAX_RETRIES`: Maximum number of retry attempts (default: 3)
- `RETRY_DELAY_SECONDS`: Delay between retry attempts (default: 60)

These can be configured in `config/.env` or `config/notifications.yml`.

## Development

This project follows a phase-wise development approach. See phase_wise_development_plan.txt for details.
