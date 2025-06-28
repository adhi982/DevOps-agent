# PowerShell script: Run all DevOps Orchestrator services and dashboard, with terminal numbers for clarity

# -----------------------------
# Initial Setup: Register GitHub webhook if needed
# -----------------------------
# Uncomment to register a GitHub webhook for automatic CI/CD triggers
# & "$PSScriptRoot\register_webhook.ps1"

# -----------------------------
# Terminal 1: Start Docker Compose (Kafka, agents, orchestrator)
# -----------------------------
# Check for and prompt for GitHub token if not set
if (-not $env:GITHUB_TOKEN -or $env:GITHUB_TOKEN -eq "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") {
    Write-Host "GitHub token not set" -ForegroundColor Yellow
    $setToken = Read-Host "Would you like to set a GitHub token now? (y/n)"
    
    if ($setToken -eq "y") {
        $tokenInput = Read-Host "Enter your GitHub personal access token" -AsSecureString
        $env:GITHUB_TOKEN = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto([System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($tokenInput))
        Write-Host "GitHub token set successfully" -ForegroundColor Green
    } else {
        $env:GITHUB_TOKEN = "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"
        Write-Host "Using default token value. Some GitHub operations may fail." -ForegroundColor Yellow
    }
} else {
    Write-Host "Using existing GitHub token from environment" -ForegroundColor Green
}

Write-Host "Starting Docker containers with docker-compose..." -ForegroundColor Cyan
docker-compose up -d

# -----------------------------
# Terminal 2: Start ngrok tunnel for orchestrator (port 8000)
# -----------------------------
Start-Process ngrok "http 8000" -WindowStyle Normal

# -----------------------------
# Wait for ngrok to start and get the public URL
# -----------------------------
Write-Host "Waiting for ngrok to start..." -ForegroundColor Cyan
Start-Sleep -Seconds 5
try {
    $ngrokStatus = Invoke-RestMethod "http://localhost:4040/api/tunnels" -ErrorAction SilentlyContinue
    if ($ngrokStatus.tunnels.Count -gt 0) {
        $webhookUrl = $ngrokStatus.tunnels[0].public_url + "/webhook"
        Write-Host "Webhook URL available: $webhookUrl" -ForegroundColor Green
        Write-Host "To configure GitHub webhooks with this URL, run:" -ForegroundColor Yellow
        Write-Host ".\register_webhook.ps1 -WebhookUrl '$webhookUrl'" -ForegroundColor White
    }
} catch {
    Write-Host "Could not get ngrok status. Run manually with \register_webhook.ps1 after ngrok is ready" -ForegroundColor Yellow
}

# -----------------------------
# Terminal 3: Monitor orchestrator logs
# -----------------------------
docker-compose logs -f orchestrator

# -----------------------------
# Terminal 4: Monitor agent logs (all agents)
# -----------------------------
docker-compose logs -f lint-agent test-agent build-agent security-agent

# -----------------------------
# Terminal 5: Set up and run the dashboard
# -----------------------------
Set-Location -Path "$PSScriptRoot\dashboard"
Write-Host "Starting dashboard with enhanced error handling..." -ForegroundColor Cyan
Write-Host "Using run_dashboard_fix.ps1 with automatic port detection and fallback options" -ForegroundColor Cyan

# Run the improved dashboard script (handles venv, port conflicts, etc.)
& "$PSScriptRoot\dashboard\run_dashboard_fix.ps1"

# Alternative options commented below in case of issues:
& "$PSScriptRoot\dashboard\dashboard_diagnose.ps1"  # Run diagnostics if issues occur
& "$PSScriptRoot\dashboard\run_dashboard.ps1"       # Basic dashboard startup
python simple_dashboard.py                         # Fallback simple dashboard if needed

# -----------------------------
# Terminal 6: (Optional) Open dashboard in browser
# -----------------------------
Start-Process "http://localhost:5000"
Write-Host "Opening DevOps dashboard at http://localhost:5000" -ForegroundColor Cyan

# -----------------------------
# Terminal 7: Test agent-dashboard connectivity 
# -----------------------------
Write-Host "Would you like to test agent-dashboard connectivity? (y/n)" -ForegroundColor Cyan
$testAgents = Read-Host
if ($testAgents -eq "y") {
    Write-Host "Running agent simulator to test dashboard connectivity..." -ForegroundColor Cyan
    Set-Location -Path "$PSScriptRoot\dashboard"
    & .\dashboard_venv\Scripts\Activate.ps1
    python agent_simulator.py
}

# -----------------------------
# Terminal 8: Dashboard Diagnostics (if needed)
# -----------------------------
Write-Host "If you encounter dashboard issues, you can run these commands:" -ForegroundColor Yellow
Write-Host "  cd dashboard" -ForegroundColor Gray
Write-Host "  .\dashboard_diagnose.ps1  # Run diagnostic checks" -ForegroundColor Gray
Write-Host "  .\fix_dashboard.ps1       # Automated fix attempts" -ForegroundColor Gray
Write-Host "  python simple_dashboard.py # Run fallback dashboard" -ForegroundColor Gray

# -----------------------------
# Git: Add, commit, and push changes with CI/CD trigger
# -----------------------------
# First check if GitHub token is set
if (-not $env:GITHUB_TOKEN -or $env:GITHUB_TOKEN -eq "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") {
    Write-Host "⚠️ GitHub token not set or is default value!" -ForegroundColor Yellow
    $setToken = Read-Host "Would you like to set a GitHub token now? (y/n)"
    if ($setToken -eq "y") {
        $env:GITHUB_TOKEN = Read-Host "Enter your GitHub token" -AsSecureString | ConvertFrom-SecureString -AsPlainText
    } else {
        Write-Host "⚠️ No GitHub token set, push operations may fail" -ForegroundColor Yellow
    }
}

# Option 1: Trigger CI/CD with real Git push
$triggerMethod = Read-Host "Select trigger method: [1] Git push (real) [2] Direct webhook (simulated) [3] Both"

if ($triggerMethod -eq "1" -or $triggerMethod -eq "3") {
    Set-Location -Path "E:\Github-adhi982\DevOps-agent\sample-project"
    Write-Host "Initializing git repository if needed..." -ForegroundColor Cyan
    if (-not (Test-Path ".git")) {
        git init
        git remote add origin https://github.com/adhi982/DevOps-agent.git
        Write-Host "Git repository initialized and remote added" -ForegroundColor Green
    }

    Write-Host "Adding changes to git..." -ForegroundColor Cyan
    git add .

    $commitMsg = Read-Host "Enter commit message [Default: Update for CI/CD pipeline trigger]"
    if (-not $commitMsg) {
        $commitMsg = "Update for CI/CD pipeline trigger"
    }
    
    Write-Host "Committing changes..." -ForegroundColor Cyan
    git commit -m $commitMsg

    # Push with GitHub token to trigger workflows
    Write-Host "Pushing changes to trigger CI/CD pipeline..." -ForegroundColor Cyan
    
    # Use token for authentication if available
    if ($env:GITHUB_TOKEN -and $env:GITHUB_TOKEN -ne "YOUR_GITHUB_TOKEN") {
        $originUrl = "https://$env:GITHUB_TOKEN@github.com/adhi982/DevOps-agent.git"
        git remote set-url origin $originUrl
    }
    
    git push -f origin main

    # Verify push was successful
    git status
    Write-Host "✅ Git push completed. Monitor the dashboard for pipeline activity." -ForegroundColor Green
}

# Option 2: Directly trigger webhook via GitHub API
if ($triggerMethod -eq "2" -or $triggerMethod -eq "3") {
    Write-Host "Manually triggering CI/CD webhook via GitHub API..." -ForegroundColor Cyan

    # Get token from environment or prompt
    $token = $env:GITHUB_TOKEN
    if (-not $token -or $token -eq "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") {
        $token = Read-Host "Enter GitHub token for API access"
    }

    $headers = @{
        "Authorization" = "token $token"
        "Accept" = "application/vnd.github.v3+json"
        "Content-Type" = "application/json"
    }

    $body = @{
        "event_type" = "manual-trigger"
        "client_payload" = @{
            "reason" = "Manual trigger from deployment script"
            "repository" = "adhi982/DevOps-agent"
            "branch" = "main"
            "commit_message" = "API-triggered build $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
        }
    } | ConvertTo-Json

    try {
        Invoke-RestMethod -Uri "https://api.github.com/repos/adhi982/DevOps-agent/dispatches" -Method Post -Headers $headers -Body $body
        Write-Host "✅ CI/CD webhook triggered successfully" -ForegroundColor Green
        Write-Host "Monitor dashboard at http://localhost:5000 for pipeline activity" -ForegroundColor Cyan
    } catch {
        Write-Host "❌ Failed to trigger CI/CD webhook: $_" -ForegroundColor Red
        Write-Host "For alternative triggering options, try: .\trigger_ci.ps1" -ForegroundColor Yellow
    }
}

# Option 3: Test with local sample
Write-Host "Would you like to also test the pipeline with local sample data? (y/n)" -ForegroundColor Cyan
$testLocal = Read-Host
if ($testLocal -eq "y") {
    Write-Host "Starting local pipeline test..." -ForegroundColor Cyan
    & "$PSScriptRoot\test_with_public_repos.py"
    
    # Verify dashboard is receiving events
    Write-Host "Local test initiated. Check the dashboard at http://localhost:5000 to monitor activity" -ForegroundColor Green
}

# -----------------------------
# Additional Helper Scripts & Monitoring Tips
# -----------------------------
Write-Host "=== HELPFUL COMMANDS & SCRIPTS ===" -ForegroundColor Magenta
Write-Host "  .\register_webhook.ps1     - Register GitHub webhook with your ngrok URL" -ForegroundColor Gray
Write-Host "  .\trigger_ci.ps1           - Manually trigger CI/CD pipeline" -ForegroundColor Gray
Write-Host "  .\monitor_agents.ps1       - View all agent logs in one terminal" -ForegroundColor Gray
Write-Host "  .\dashboard\agent_simulator.py - Test dashboard connectivity" -ForegroundColor Gray
Write-Host "" -ForegroundColor Gray
Write-Host "=== MONITORING TIPS ===" -ForegroundColor Magenta
Write-Host "  1. Dashboard URL: http://localhost:5000" -ForegroundColor Cyan
Write-Host "  2. Check agent health on dashboard status page" -ForegroundColor Cyan
Write-Host "  3. Monitor Kafka topics with: docker exec -it devops-orchestrator_kafka_1 kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic agent.results" -ForegroundColor Cyan
Write-Host "  4. View all agent logs: .\monitor_agents.ps1" -ForegroundColor Cyan
Write-Host "  5. Test dashboard connectivity: cd dashboard && python agent_simulator.py" -ForegroundColor Cyan

# --- End of script ---

# Project Development Plan for DevOps-Orchestrator

# Phase 1: Project Initialization
# - Tasks:
#   1. Set up the project structure.
#   2. Initialize version control (e.g., Git).
#   3. Create a README file with project goals and setup instructions.
# - Verification:
#   - Ensure all directories and files are created as per the structure.
#   - Verify Git repository is initialized.
# - Expected Output:
#   - A clean project structure with version control.
# - Confirmation:
#   - Run `git status` to confirm the repository is initialized.

# Phase 2: Core Functionality Development
# - Tasks:
#   1. Develop the orchestrator script (main.py).
#   2. Implement agent scripts (build_agent, lint_agent, etc.).
#   3. Set up Kafka for communication between orchestrator and agents.
# - Verification:
#   - Test each agent independently.
#   - Verify Kafka setup by sending and receiving test messages.
# - Expected Output:
#   - Functional orchestrator and agents.
# - Confirmation:
#   - Run each agent script and check logs for successful execution.

# Phase 3: Integration Testing
# - Tasks:
#   1. Integrate orchestrator with all agents.
#   2. Test end-to-end workflows.
# - Verification:
#   - Run the orchestrator and ensure all agents are triggered.
#   - Check logs for successful task completion.
# - Expected Output:
#   - Smooth communication and task execution across all components.
# - Confirmation:
#   - Run `monitor_agents.ps1` to verify agent statuses.

# Phase 4: Dashboard Development
# - Tasks:
#   1. Develop a web-based dashboard for monitoring.
#   2. Integrate the dashboard with the orchestrator.
# - Verification:
#   - Access the dashboard and verify data is displayed correctly.
# - Expected Output:
#   - A functional dashboard showing real-time statuses.
# - Confirmation:
#   - Open the dashboard in a browser and check for live updates.

# Phase 5: Deployment and Monitoring
# - Tasks:
#   1. Create Dockerfiles for containerization.
#   2. Deploy the application using Docker Compose.
#   3. Set up monitoring and alerting.
# - Verification:
#   - Run `docker-compose up` and ensure all services are running.
#   - Test monitoring and alerting by simulating failures.
# - Expected Output:
#   - A fully deployed and monitored application.
# - Confirmation:
#   - Check logs and monitoring tools for successful deployment.

# Phase 6: Maintenance and Scaling
# - Tasks:
#   1. Optimize code and infrastructure for scalability.
#   2. Add new features as required.
# - Verification:
#   - Conduct load testing to ensure scalability.
# - Expected Output:
#   - A scalable and maintainable application.
# - Confirmation:
#   - Run load tests and analyze results for performance metrics.
