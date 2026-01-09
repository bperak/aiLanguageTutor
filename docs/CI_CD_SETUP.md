# CI/CD Setup Guide

This guide explains how to set up and use the CI/CD pipeline for E2E tests.

## Overview

The project includes two GitHub Actions workflows:

1. **`e2e-tests.yml`** - Fast test suite (runs on every push/PR)
2. **`e2e-tests-full.yml`** - Complete test suite (runs daily or manually)

## Quick Setup

### 1. Add GitHub Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions, and add:

- `OPENAI_API_KEY` - Your OpenAI API key
- `GEMINI_API_KEY` - Your Google Gemini API key  
- `GOOGLE_CLOUD_PROJECT_ID` - Your Google Cloud project ID

### 2. Verify Workflows

The workflows are already configured in `.github/workflows/`. They will automatically:
- Run on push to `main`/`develop` branches
- Run on pull requests
- Run daily at 2 AM UTC (full suite only)

### 3. Manual Trigger

You can manually trigger workflows:

```bash
# Trigger fast suite
gh workflow run e2e-tests.yml

# Trigger full suite
gh workflow run e2e-tests-full.yml

# Trigger with all scenarios option
gh workflow run e2e-tests.yml -f run_all_scenarios=true
```

## Workflow Details

### Fast Suite (`e2e-tests.yml`)

**Runs on:** Push, PR, Manual

**Scenarios:**
- `smoke.json` (~10s)
- `no_dev_next_endpoints.json` (~5s)
- `home_status_e2e.json` (~10s)
- `login_e2e.json` (~15s)
- `lexical_graph_e2e.json` (~15s)
- `prelesson_kit_flow.json` (~10s)

**Total time:** ~1-2 minutes

**Use case:** Quick validation on every commit

### Full Suite (`e2e-tests-full.yml`)

**Runs on:** Daily schedule (2 AM UTC), Manual

**Scenarios:** All scenarios including:
- `full_registration_e2e.json` (~2-3 min)
- `grammar_study_e2e.json` (~20s)
- `cando_lesson_e2e.json` (~30s)
- `profile_build_schema.json` (~30s)
- Plus all fast scenarios

**Total time:** ~5-10 minutes

**Use case:** Comprehensive validation

## Local Testing

Test the CI/CD setup locally:

```bash
# Simulate CI/CD environment
COMPOSE_FILE_PATH=docker-compose.server.yml \
TARGET_BACKEND=http://backend:8000 \
TARGET_FRONTEND=http://frontend:3000 \
./scripts/run-e2e-tests.sh
```

## Troubleshooting CI/CD

### Tests Failing in CI

1. **Check workflow logs** in GitHub Actions
2. **Verify secrets** are set correctly
3. **Check service health** - logs show if services started properly
4. **Review timeout** - some scenarios may need more time in CI

### Services Not Starting

The workflow waits up to 180 seconds for services to be healthy. If this fails:

1. Check Docker image builds
2. Verify database connections
3. Review service logs in workflow output

### Timeout Issues

Increase timeout in workflow:

```yaml
timeout-minutes: 60  # Increase from 30
```

Or in scenario:

```javascript
// Increase wait time
await new Promise(r => setTimeout(r, 15000)); // 15 seconds
```

## Customization

### Add New Scenarios to CI

Edit `.github/workflows/e2e-tests.yml`:

```yaml
- name: Run E2E tests
  run: |
    ./scripts/run-e2e-tests.sh \
      /work/scenarios/my_new_scenario.json
```

### Change Schedule

Edit `.github/workflows/e2e-tests-full.yml`:

```yaml
on:
  schedule:
    - cron: '0 2 * * *'  # Change time here
```

### Add More Secrets

1. Add to GitHub Secrets
2. Add to workflow `.env` creation step:

```yaml
- name: Create .env file
  run: |
    cat > .env << EOF
    MY_NEW_SECRET=${MY_NEW_SECRET}
    EOF
  env:
    MY_NEW_SECRET: ${{ secrets.MY_NEW_SECRET }}
```

## Best Practices

1. **Keep fast suite fast** - Only include quick scenarios in PR workflow
2. **Monitor CI costs** - Full suite runs daily, not on every commit
3. **Use manual triggers** - For debugging, use manual workflow dispatch
4. **Review logs** - Check service logs on failure to debug issues
5. **Test locally first** - Run scenarios locally before pushing

## Integration with Other CI/CD

### GitLab CI

Create `.gitlab-ci.yml`:

```yaml
e2e-tests:
  image: docker:latest
  services:
    - docker:dind
  before_script:
    - apk add --no-cache docker-compose
  script:
    - docker compose -f docker-compose.server.yml up -d
    - ./scripts/run-e2e-tests.sh
```

### Jenkins

Create `Jenkinsfile`:

```groovy
pipeline {
    agent any
    stages {
        stage('E2E Tests') {
            steps {
                sh './scripts/run-e2e-tests.sh'
            }
        }
    }
}
```

## Resources

- **Workflows**: `.github/workflows/*.yml`
- **Test Runner**: `scripts/run-e2e-tests.sh`
- **E2E Guide**: `docs/E2E_TESTING.md`
- **Scenarios**: `tests/mcp/scenarios/*.json`
