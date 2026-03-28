# Environment Configuration Matrix

Comprehensive environment configuration covering branch mapping, approvals, secrets, deployment strategies, and rollback procedures.

---

## Environment Overview

| Property | Development | Staging | Production |
|---|---|---|---|
| **Branch** | `develop`, `feature/*` | `release/*`, `main` (auto) | `main` (manual approval) |
| **URL** | `dev.example.com` | `staging.example.com` | `example.com` |
| **Replicas** | 1 | 2 | 3+ (auto-scaled) |
| **Database** | Shared dev DB | Isolated staging DB | HA production cluster |
| **Log Level** | `DEBUG` | `INFO` | `WARN` |
| **Source Maps** | Yes | Yes | No |
| **SSL** | Self-signed | ACM | ACM |
| **CDN** | No | Optional | CloudFront |
| **Monitoring** | Basic | Full (no alerts) | Full + PagerDuty |
| **Data** | Seed/synthetic | Anonymized prod copy | Real |
| **Backup** | None | Daily | Continuous + PITR |

---

## Branch-to-Environment Mapping

```yaml
# Branch mapping configuration
branch_mapping:
  develop:
    environment: development
    auto_deploy: true
    approval_required: false
    protection_rules: []

  "feature/*":
    environment: development
    auto_deploy: false
    approval_required: false
    note: "Deploy via manual workflow dispatch"

  "release/*":
    environment: staging
    auto_deploy: true
    approval_required: false
    protection_rules:
      - required_status_checks: [lint, test, build]

  main:
    environment: production
    auto_deploy: false
    approval_required: true
    protection_rules:
      - required_status_checks: [lint, test, build, integration-test]
      - required_reviewers: 2
      - dismiss_stale_reviews: true
      - require_code_owner_reviews: true
```

### GitHub Actions Environment Config

```yaml
deploy:
  runs-on: ubuntu-latest
  environment:
    name: ${{ github.ref == 'refs/heads/main' && 'production' || 'staging' }}
    url: ${{ github.ref == 'refs/heads/main' && 'https://example.com' || 'https://staging.example.com' }}
  steps:
    - name: Deploy
      run: ./deploy.sh ${{ vars.ENVIRONMENT }}
```

---

## Approval Gates

### Gate Matrix

| Gate | Development | Staging | Production |
|---|---|---|---|
| **CI Checks Pass** | Required | Required | Required |
| **Code Review** | Optional | 1 reviewer | 2 reviewers |
| **Manual Approval** | No | No | Yes (team lead) |
| **Security Scan** | No | SAST only | SAST + DAST |
| **Performance Test** | No | Optional | Required (p95 < 200ms) |
| **Change Window** | Anytime | Business hours | Tue-Thu 10am-2pm ET |
| **Rollback Plan** | N/A | Documented | Documented + tested |

### GitHub Environment Protection Rules

```yaml
# Configured via GitHub Settings > Environments
environments:
  production:
    protection_rules:
      required_reviewers:
        - team: platform-leads
        - user: cto
      wait_timer: 5  # minutes
      deployment_branch_policy:
        protected_branches: true
        custom_branches: []

  staging:
    protection_rules:
      required_reviewers: []
      wait_timer: 0
      deployment_branch_policy:
        protected_branches: false
        custom_branches:
          - "release/*"
          - "main"
```

### Approval Workflow

```yaml
jobs:
  request-approval:
    runs-on: ubuntu-latest
    environment: production
    steps:
      - name: Deployment approved
        run: echo "Approval received, proceeding with deployment"

  deploy:
    needs: request-approval
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to production
        run: ./scripts/deploy.sh production
```

---

## Secrets Management

### Secret Categories

| Category | Scope | Rotation | Storage |
|---|---|---|---|
| **API Keys** | Environment | 90 days | GitHub Secrets |
| **Database Credentials** | Environment | 30 days | AWS Secrets Manager |
| **TLS Certificates** | Environment | Auto (ACM) | AWS ACM |
| **Service Tokens** | Repository | 180 days | GitHub Secrets |
| **SSH Keys** | Repository | 365 days | GitHub Secrets |
| **Cloud IAM** | Environment | Session (OIDC) | AWS IAM Roles |

### OIDC Federation (No Long-Lived Secrets)

```yaml
permissions:
  id-token: write
  contents: read

steps:
  - uses: aws-actions/configure-aws-credentials@v4
    with:
      role-to-arn: arn:aws:iam::${{ secrets.AWS_ACCOUNT_ID }}:role/github-actions-${{ vars.ENVIRONMENT }}
      aws-region: us-east-1
      role-session-name: gha-${{ github.run_id }}
```

### Environment-Scoped Secrets

```yaml
# Access environment-specific secrets automatically
steps:
  - name: Connect to database
    run: ./migrate.sh
    env:
      # These resolve to different values per environment
      DATABASE_URL: ${{ secrets.DATABASE_URL }}
      REDIS_URL: ${{ secrets.REDIS_URL }}
      API_KEY: ${{ secrets.API_KEY }}
```

### Secret Scanning Prevention

```yaml
# .github/workflows/secret-scan.yml
name: Secret Scan
on: [push, pull_request]
jobs:
  scan:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: trufflesecurity/trufflehog@main
        with:
          extra_args: --only-verified
```

---

## Deployment Strategies

### Blue-Green Deployment

Zero-downtime deployment by maintaining two identical environments.

```
                    ┌──────────────┐
                    │  Load        │
     Traffic ──────►│  Balancer    │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              ▼                         ▼
     ┌────────────────┐       ┌────────────────┐
     │  Blue (v1)     │       │  Green (v2)    │
     │  ● Active      │       │  ● Idle/New    │
     │  Port 8080     │       │  Port 8081     │
     └────────────────┘       └────────────────┘
```

```yaml
# blue-green-deploy.yml
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production
    steps:
      - name: Deploy to green
        run: |
          aws ecs update-service \
            --cluster ${{ vars.CLUSTER }} \
            --service ${{ vars.SERVICE }}-green \
            --task-definition ${{ steps.task-def.outputs.task-definition-arn }}

      - name: Health check green
        run: |
          for i in $(seq 1 30); do
            STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://green.example.com/health)
            if [ "$STATUS" = "200" ]; then
              echo "Green is healthy"
              exit 0
            fi
            sleep 10
          done
          echo "Health check failed"
          exit 1

      - name: Switch traffic to green
        run: |
          aws elbv2 modify-listener \
            --listener-arn ${{ vars.LISTENER_ARN }} \
            --default-actions Type=forward,TargetGroupArn=${{ vars.GREEN_TG_ARN }}

      - name: Verify production
        run: |
          sleep 30
          STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://example.com/health)
          [ "$STATUS" = "200" ] || exit 1
```

**When to use:** Mission-critical services where instant rollback is required.

### Canary Deployment

Gradually shift traffic to the new version.

```
     Traffic ──────► Load Balancer
                         │
                    ┌────┴────┐
                    │ Weights  │
                    └────┬────┘
              95%        │        5%
              ┌──────────┼──────────┐
              ▼                     ▼
     ┌────────────────┐    ┌────────────────┐
     │  Stable (v1)   │    │  Canary (v2)   │
     └────────────────┘    └────────────────┘
```

```yaml
# canary-deploy.yml
jobs:
  canary:
    runs-on: ubuntu-latest
    environment: production
    strategy:
      max-parallel: 1
      matrix:
        weight: [5, 25, 50, 100]
    steps:
      - name: Set canary weight to ${{ matrix.weight }}%
        run: |
          aws elbv2 modify-rule \
            --rule-arn ${{ vars.CANARY_RULE_ARN }} \
            --actions '[
              {"Type":"forward","ForwardConfig":{"TargetGroups":[
                {"TargetGroupArn":"${{ vars.STABLE_TG }}","Weight":$((100-${{ matrix.weight }}))},
                {"TargetGroupArn":"${{ vars.CANARY_TG }}","Weight":${{ matrix.weight }}}
              ]}}'

      - name: Monitor error rate (5 min)
        run: |
          sleep 300
          ERROR_RATE=$(aws cloudwatch get-metric-statistics \
            --namespace "AWS/ApplicationELB" \
            --metric-name "HTTPCode_Target_5XX_Count" \
            --start-time $(date -d '-5 min' -u +%Y-%m-%dT%H:%M:%S) \
            --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
            --period 300 \
            --statistics Sum \
            --query 'Datapoints[0].Sum' --output text)
          echo "Error rate: $ERROR_RATE"
          if [ "$ERROR_RATE" != "None" ] && [ "$ERROR_RATE" -gt 10 ]; then
            echo "::error::Error threshold exceeded, triggering rollback"
            exit 1
          fi
```

**When to use:** High-traffic services where you want to validate with real users before full rollout.

### Rolling Deployment

Update instances incrementally within the existing fleet.

```yaml
# ECS Rolling Update configuration
resource "aws_ecs_service" "app" {
  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
}
```

```yaml
# rolling-deploy.yml
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production
    steps:
      - name: Rolling update
        run: |
          aws ecs update-service \
            --cluster ${{ vars.CLUSTER }} \
            --service ${{ vars.SERVICE }} \
            --task-definition ${{ steps.task-def.outputs.arn }} \
            --deployment-configuration "minimumHealthyPercent=50,maximumPercent=200"

      - name: Wait for stable
        run: |
          aws ecs wait services-stable \
            --cluster ${{ vars.CLUSTER }} \
            --services ${{ vars.SERVICE }}
```

**When to use:** Standard applications where brief mixed-version traffic is acceptable.

---

## Rollback Procedures

### Automated Rollback Triggers

| Metric | Threshold | Window | Action |
|---|---|---|---|
| **5xx Error Rate** | > 5% | 5 min | Auto rollback |
| **p99 Latency** | > 2000ms | 5 min | Auto rollback |
| **Health Check Failures** | > 3 consecutive | 90s | Auto rollback |
| **CPU Usage** | > 90% sustained | 10 min | Alert + manual |
| **Memory Usage** | > 85% sustained | 10 min | Alert + manual |

### ECS Automatic Rollback

```yaml
- name: Deploy with rollback
  run: |
    aws ecs update-service \
      --cluster ${{ vars.CLUSTER }} \
      --service ${{ vars.SERVICE }} \
      --task-definition ${{ env.NEW_TASK_DEF }} \
      --deployment-configuration '{
        "deploymentCircuitBreaker": {
          "enable": true,
          "rollback": true
        },
        "minimumHealthyPercent": 100,
        "maximumPercent": 200
      }'
```

### Manual Rollback Workflow

```yaml
# .github/workflows/rollback.yml
name: Rollback

on:
  workflow_dispatch:
    inputs:
      environment:
        description: "Target environment"
        required: true
        type: choice
        options: [staging, production]
      version:
        description: "Version/tag to roll back to (e.g., sha-abc1234)"
        required: true
        type: string
      reason:
        description: "Rollback reason"
        required: true
        type: string

permissions:
  contents: read
  id-token: write

jobs:
  rollback:
    runs-on: ubuntu-latest
    environment: ${{ inputs.environment }}
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4

      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-arn: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: us-east-1

      - name: Log rollback
        run: |
          echo "Rolling back ${{ inputs.environment }} to ${{ inputs.version }}"
          echo "Reason: ${{ inputs.reason }}"
          echo "Initiated by: ${{ github.actor }}"
          echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

      - name: Pull previous image
        run: |
          IMAGE="${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ inputs.version }}"
          docker pull "$IMAGE"

      - name: Update task definition
        id: task-def
        run: |
          CURRENT=$(aws ecs describe-services \
            --cluster ${{ vars.CLUSTER }} \
            --services ${{ vars.SERVICE }} \
            --query 'services[0].taskDefinition' --output text)

          NEW_DEF=$(aws ecs describe-task-definition \
            --task-definition "$CURRENT" \
            --query 'taskDefinition' | \
            jq --arg IMG "${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ inputs.version }}" \
              '.containerDefinitions[0].image = $IMG |
               del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .compatibilities, .registeredAt, .registeredBy)')

          ARN=$(echo "$NEW_DEF" | \
            aws ecs register-task-definition --cli-input-json file:///dev/stdin \
            --query 'taskDefinition.taskDefinitionArn' --output text)

          echo "arn=$ARN" >> "$GITHUB_OUTPUT"

      - name: Deploy rollback
        run: |
          aws ecs update-service \
            --cluster ${{ vars.CLUSTER }} \
            --service ${{ vars.SERVICE }} \
            --task-definition ${{ steps.task-def.outputs.arn }} \
            --force-new-deployment

      - name: Wait for stable
        run: |
          aws ecs wait services-stable \
            --cluster ${{ vars.CLUSTER }} \
            --services ${{ vars.SERVICE }}

      - name: Verify health
        run: |
          STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://${{ vars.APP_URL }}/health)
          if [ "$STATUS" != "200" ]; then
            echo "::error::Health check failed after rollback"
            exit 1
          fi
          echo "Rollback successful. Service is healthy."

      - name: Notify team
        if: always()
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "Rollback ${{ job.status }}: ${{ inputs.environment }} → ${{ inputs.version }}\nReason: ${{ inputs.reason }}\nBy: ${{ github.actor }}"
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
```

### Rollback Decision Tree

```
Incident Detected
       │
       ▼
  Is service down?
   ┌───┴───┐
   Yes     No
   │       │
   ▼       ▼
 Immediate   Is error rate > 5%?
 rollback    ┌───┴───┐
             Yes     No
             │       │
             ▼       ▼
           Canary    Monitor for
           rollback  15 more min
             │           │
             ▼           ▼
           Full      Escalating?
           rollback  ┌───┴───┐
           if needed Yes     No
                     │       │
                     ▼       ▼
                   Rollback  Continue
                             monitoring
```
