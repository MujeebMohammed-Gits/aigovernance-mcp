  #### 5. Rollback Procedure Document

  # MCP Control-Tower - Rollback Procedure

  ## Overview

  This document defines the rollback procedures for the MCP Control-Tower application,
  ensuring safe and rapid recovery from deployment failures.

  ### Triggers for Rollback

  Rollback should be initiated when any of the following conditions are detected:

  1. **Health Check Failures**: `/health` endpoint returns non-200 status for >5 minutes
  2. **Circuit Breaker Trips**: >3 circuit breaker trips in 10 minutes across any provider
  3. **Error Rate Spike**: HTTP 5xx errors >5% of total requests in 10-minute window
  4. **PII Blocking**: Sudden increase in PII-blocked calls affecting critical workflows
  5. **Customer-Impacting Errors**: Support team receives ≥3 customer complaints about service
  6. **Security Alerts**: Detected security vulnerabilities or breach indicators

  ### Rollback Types

  #### Type A: Immediate Rollback (Emergency)

  **Time Target**: <10 minutes from detection

  **Use Case**: Critical production outage, security incident, complete service failure

  ```bash
  # IMMEDIATE ROLLBACK COMMANDS

  # 1. Stop current production services
  docker-compose -f docker-compose.prod.yml down --remove-orphans

  # 2. Pull and restart previous stable version
  # Option A: Using docker compose restart with existing image
  docker-compose -f docker-compose.prod.yml up -d

  # Option B: Explicit image pull and restart
  docker pull mujeebmohammed/aigovernance-mcp:prev-version
  docker-compose -f docker-compose.prod.yml up -d

  # 3. Verify services are running
  docker ps --filter "name=aigovernance-prod"

  # 4. Verify health status
  docker ps --filter "name=aigovernance-prod" --format "{{.HealthStatus}}"

  # 5. Confirm functionality
  curl -f http://localhost/health || exit 1

  # 6. Notify stakeholders
  # - Slack: #deployment-alerts (emoji: 🚨)
  # - Email: devops-lead@yourcompany.com
  # - SMS if critical (optional)

  # 7. Create incident record
  # - Jira: Create incident with type "Rollback"
  # - Document: Time of failure, time of rollback, root cause

  #### Type B: Planned Rollback (Maintenance)

  Time Target: 24-48 hours advance notice

  Use Case: Scheduled maintenance, feature deprecation, capacity planning

  # PLANNED ROLLBACK COMMANDS

  # 1. Notify stakeholders 24 hours in advance
  # - Slack announcement: #deployment-schedule
  # - Email to leadership: 24-hour notice
  # - Jira: Create change request with timeline

  # 2. Deploy new version to Development first
  docker-compose -f docker-compose.dev.yml up -d
  sleep 30
  # Verify: docker ps --filter "name=aigovernance-dev"

  # 3. Run validation tests
  python -m pytest tests/ -v --tb=short
  # Verify: All tests pass

  # 4. Promote to Staging
  docker-compose -f docker-compose.staging.yml up -d
  sleep 30
  # Verify: docker ps --filter "name=aigovernance-staging"

  # 5. Run staging integration tests
  # - Manual smoke tests
  # - API endpoint validation
  # - Dashboard data verification

  # 6. Deploy to Production with monitoring window
  docker-compose -f docker-compose.prod.yml up -d
  # Monitor for 30 minutes minimum

  # 7. If no issues detected, mark rollout successful
  # 8. If issues detected, execute Type A immediate rollback

  # 9. Document outcome
  # - Jira: Close rollback ticket
  # - Confluence: Update deployment plan
  # - Slack: #deployment-announce

  ### Rollback Verification Checklist

  ## Post-Rollback Verification

  ### Immediate Verification (within 2 minutes of rollback)
  - [ ] All services running: `docker ps` shows expected containers
  - [ ] Health checks passing: `docker ps --format "{{.HealthStatus}}"` shows healthy
  - [ ] API responding: `curl /health` returns 200
  - [ ] No new error logs in last 2 minutes

  ### Short-Term Verification (within 10 minutes)
  - [ ] Error rate returned to baseline (<1% HTTP 5xx)
  - [ ] Circuit breakers reset and allowing traffic
  - [ ] Rate limits restored to normal
  - [ ] Audit logging operational
  - [ ] Monitoring dashboards showing normal activity

  ### Medium-Term Verification (within 1 hour)
  - [ ] All original features functional
  - [ ] No regression in performance
  - [ ] User-facing issues resolved
  - [ ] Support ticket resolution in progress (if applicable)
  - [ ] Stakeholder notification completed

  ### Long-Term Verification (within 24 hours)
  - [ ] Root cause analysis completed
  - [ ] Post-mortem documentation written
  - [ ] Prevention measures implemented
  - [ ] Rollback test documented (if applicable)
  - [ ] Lessons learned shared with team

  ### Rollback Communication Plan

  ## Stakeholder Communication

  ### Immediately (within 5 minutes)
  - **On-call DevOps**: Page via pager/phone
  - **Technical Lead**: Email and Slack DM
  - **Security Officer**: If security-related incident

  ### Within 15 minutes
  - **Development Team**: Slack #channel
  - **Compliance Team**: Email if PII/data involved
  - **Customer Support**: Internal briefing for customer inquiries

  ### Within 1 hour
  - **Executive Leadership**: Email summary
  - **Product Management**: Slack announcement
  - **Customer Success**: Prepare customer response if needed

  ### Within 24 hours
  - **All Stakeholders**: Post-mortem summary email
  - **Documentation**: Update rollback procedure
  - **Team Meeting**: Discuss root cause and prevention

  ### Sample Slack Message (Emergency Rollback)

  :rotating_light: EMERGENCY ROLLBACK :rotating_light:

  Production deployment rolled back at 14:30 UTC.
  Root cause: Circuit breaker storm causing 97% error rate.
  Rollback completed at 14:40 UTC.
  Services restored. Root cause analysis in progress.
  Stay tuned for updates.

  #deployment-alerts #on-call


  ### Sample Email (Post-Rollback)


  Subject: Rollback Complete - MCP Control-Tower Production

  Team,

  Production rollback completed successfully at 14:40 UTC.

  Issue: Circuit breaker storm causing 97% error rate across all AI providers.
  Detection: Health checks failing, error rate spikes detected at 14:20 UTC.
  Rollback: Initiated at 14:30 UTC, completed at 14:40 UTC.
  Duration: 10 minutes of degraded service.

  Root Cause: (Pending analysis - placeholder)

  Actions Taken:

  - Docker compose down and restart
  - Circuit breakers reset
  - Health checks verified
  - Monitoring restored

  Prevention Measures (pending root cause analysis):

  - Circuit breaker configuration review
  - Increased recovery timeout
  - Additional monitoring alerts

  Next Steps:

  - Root cause analysis due by EOD
  - Post-mortem scheduled for tomorrow
  - Prevention measures implementation timeline

  Services are fully operational. Thank you for your patience.

  Best regards,
  DevOps Team


