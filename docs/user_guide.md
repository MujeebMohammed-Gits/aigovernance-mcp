#### 3. End-user Guide

  # AI Governance & Compliance Control-Tower - User Guide

  ## Table of Contents
  1. [Installation](#installation)
  2. [Configuration](#configuration)
  3. [Daily Operations](#daily-operations)
  4. [Deployment](#deployment)
  5. [Governance Workflows](#governance-workflows)
  6. [Troubleshooting](#troubleshooting)
  7. [Security](#security)

  ---

  ## Installation

  ### Prerequisites
  - Python 3.11 or higher
  - Docker and Docker Compose (optional, for containerized deployment)
  - Git (for version control)
  - Access to AI provider accounts (OpenAI, Anthropic, Google)

  ### Quick Start

  ```bash
  # Clone the repository
  git clone https://github.com/MujeebMohammed-Gits/aigovernance-mcp.git
  cd aigovernance-mcp

  # Install dependencies
  pip install -r requirements.txt

  # Configure environment variables
  cp .env.example .env
  # Edit .env with your API keys and configuration

  # Start the application
  # Option 1: Direct execution
  python server.py

  # Option 2: Using Docker Compose
  docker-compose up -d

  # Option 3: Using Kubernetes (production)
  kubectl apply -f k8s/

  ### Environment Configuration

  Copy .env.example to .env and configure the following:

   Variable             Description            Example
  ━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━
   OPENAI_API_KEY       OpenAI API key         sk-pro-...
  ───────────────────  ─────────────────────  ─────────────────────────
   ANTHROPIC_API_KEY    Anthropic API key      sk-ant-...
  ───────────────────  ─────────────────────  ─────────────────────────
   GOOGLE_API_KEY       Google AI API key      AQ.A-...
  ───────────────────  ─────────────────────  ─────────────────────────
   HOST                 Server bind address    0.0.0.0
  ───────────────────  ─────────────────────  ─────────────────────────
   PORT                 Server port            8000
  ───────────────────  ─────────────────────  ─────────────────────────
   DEBUG                Debug mode             False
  ───────────────────  ─────────────────────  ─────────────────────────
   LOG_LEVEL            Logging level          INFO
  ───────────────────  ─────────────────────  ─────────────────────────
   SECRET_KEY           Application secret     Change in production
  ───────────────────  ─────────────────────  ─────────────────────────
   ALLOWED_HOSTS        Allowed hosts          localhost,127.0.0.1
  ───────────────────  ─────────────────────  ─────────────────────────
   DEFAULT_PROVIDER     Default AI provider    openai
  ───────────────────  ─────────────────────  ─────────────────────────
   DEFAULT_MODEL        Default model          gpt-4

  ———

  ## Daily Operations

  ### Starting the Dashboard

  # Start the monitoring dashboard
  python -m dashboard.dashboard

  # Access at: http://127.0.0.1:5000

  ### Checking System Health

  # Health check endpoint
  curl http://localhost:8000/health

  # Expected response:
  # {
  #   "status": "healthy",
  #   "providers": {"openai": true, "anthropic": true, "google": true},
  # "uptime": 3600,
  # "version": "2.0.0"
  # }

  ### Viewing Audit Logs

  # View recent audit events
  tail -f logs/mcp_control_tower.log

  # Or query via API
  curl http://localhost:8000/audit/events?limit=50

  ———

  ## Deployment

  ### Development Deployment

  # Using Docker Compose
  docker compose -f docker-compose.dev.yml up -d

  # Verify deployment
  docker ps --filter "name=aigovernance-dev"

  # View logs
  docker logs aigovernance-dev

  ### Staging Deployment

  # Using Docker Compose
  docker compose -f docker-compose.staging.yml up -d

  # Verify deployment
  docker ps --filter "name=aigovernance-staging"

  ### Production Deployment

  # Using Docker Compose with CI/CD
  docker compose -f docker-compose.prod.yml up -d

  # Verify deployment with health check
  docker ps --filter "name=aigovernance-prod"

  # Check health status
  docker ps --filter "name=aigovernance-prod" --format "{{.HealthStatus}}"

  ### Rolling Deployment Strategy

  1. Deploy to Development → Verify health checks pass
  2. Promote to Staging → Run integration tests
  3. Promote to Production → After security review
  4. Monitor → Watch dashboards for 30 minutes
  5. Rollback → If issues detected: docker-compose down

  ### Post-Deployment Checklist

  - [ ] Health check endpoint returns 200
  - [ ] All API keys are configured
  - [ ] Circuit breakers are reset
  - [ ] Rate limits are within bounds
  - [ ] Audit logging is active
  - [ ] Monitoring dashboards are displaying data
  - [ ] Slack notifications are configured

  ———

  ## Governance Workflows

  ### PII Detection & Approval Workflow

  graph TD
      A[AI Call Request] --> B{Policy Engine Evaluation}
      B -->|Allow| C[Proceed with Call]
      B -->|Block| D[Request PII Approval]
      B -->|Warn| E[Log and Continue with Warning]

      D -->|Approved| F[Resume Call with Logging]
      D -->|Rejected| G[Return Error to User]

  ### Policy Violation Response

  1. Detection: Policy engine identifies violation (PII, risk level, etc.)
  2. Action: Block/Warn/Limit based on configuration
  3. Logging: Event recorded in audit logger
  4. Notification: Slack alert sent to compliance channel
  5. Review: Compliance team reviews incident
  6. Resolution: Policy updated or approval granted

  ———

  ## Troubleshooting

  ### Common Issues

   Problem                  Cause                      Solution
  ━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Server won't start       Missing API keys           Check .env file configuration
  ───────────────────────  ─────────────────────────  ───────────────────────────────────────────────────────
   High latency             Circuit breaker open       Wait for recovery timeout or check upstream service
  ───────────────────────  ─────────────────────────  ───────────────────────────────────────────────────────
   Rate limit exceeded      Too many requests          Reduce request frequency or increase rate limit
  ───────────────────────  ─────────────────────────  ───────────────────────────────────────────────────────
   PII blocking calls       PII detected in request    Review data and either remove PII or request approval
  ───────────────────────  ─────────────────────────  ───────────────────────────────────────────────────────
   Dashboard not loading    Port conflict              Change PORT environment variable
  ───────────────────────  ─────────────────────────  ───────────────────────────────────────────────────────
   Health check failing     Service not ready          Wait for startup complete, check logs

  ### Error Codes

  - 400 - Bad request (invalid parameters)
  - 401 - Unauthorized (missing/invalid API key)
  - 403 - Forbidden (insufficient permissions)
  - 429 - Rate limit exceeded
  - 503 - Service unavailable (circuit breaker open)

  ———

  ## Security

  ### Data Handling

  - PII Data: All PII is classified and may be blocked based on configuration
  - API Keys: Never commit API keys to version control - use .env or secret management
  - Data Classification: Internal, Confidential, Restricted - set per-agent in agent registry
  - Access Control: Use ALLOWED_HOSTS to restrict who can access the server

  ### Compliance

  - GDPR: Data classification and PII handling comply with GDPR requirements
  - EU AI Act: Policy engine enforces risk-based requirements
  - Audit Trails: All events logged with immutable audit records
  - Retention: Audit logs retained per company policy (default 90 days)

  ———

  ## Version History

   Version    Date          Changes
  ━━━━━━━━━  ━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   1.0.0      2026-09-01    Initial release
  ─────────  ────────────  ───────────────────────────────────────────────────────
   1.1.0      2026-09-09    CI/CD pipeline, automated tests added
  ─────────  ────────────  ───────────────────────────────────────────────────────
   2.0.0      2026-09-09    Production deployment pipeline, environment promotion

  ———

  ## Need Help?

  - Documentation: https://yourdomain.com/docs
  - Issues: GitHub Issues repository
  - Support: compliance@yourcompany.com
