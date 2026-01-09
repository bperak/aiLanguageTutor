# E2E Testing Guide

This guide covers how to run, debug, and extend the E2E test suite for AI Language Tutor.

## Overview

The E2E test suite uses **Playwright MCP Runner** to execute browser-based scenarios defined as JSON files. Tests run in a Docker container with headless Chromium.

## Quick Start

### Run All Tests
```bash
./scripts/run-e2e-tests.sh
```

### Run Specific Scenarios
```bash
./scripts/run-e2e-tests.sh \
  /work/scenarios/smoke.json \
  /work/scenarios/login_e2e.json
```

### Run Registration E2E Only
```bash
./scripts/check-registration-e2e
```

### Run Standard Smoke Tests
```bash
./scripts/check-pwy
```

## Available Scenarios

| Scenario | Description | Duration |
|----------|-------------|----------|
| `smoke.json` | Basic health checks (frontend, backend, lexical graph) | ~10s |
| `no_dev_next_endpoints.json` | Verify dev-only endpoints are not accessible | ~5s |
| `home_status_e2e.json` | Home page loads without 500 errors | ~10s |
| `login_e2e.json` | Login form validation and submission | ~15s |
| `full_registration_e2e.json` | Complete registration → profile → learning path | ~2-3min |
| `profile_build_schema.json` | Profile building via API | ~30s |
| `lexical_graph_e2e.json` | Lexical graph page loads and renders | ~15s |
| `grammar_study_e2e.json` | Grammar study page navigation | ~20s |
| `cando_lesson_e2e.json` | CanDo lesson page navigation | ~30s |
| `prelesson_kit_flow.json` | Pre-lesson kit session creation | ~10s |

## Scenario Structure

Each scenario is a JSON file with this structure:

```json
{
  "name": "scenario-name",
  "description": "What this scenario tests",
  "steps": [
    {
      "action": "navigate",
      "url": "http://localhost:3000/page"
    },
    {
      "action": "evaluate",
      "function": "async () => { /* browser code */ }",
      "saveAs": "resultName"
    },
    {
      "action": "assert",
      "expression": "resultName.property === expected"
    }
  ]
}
```

### Actions

#### `navigate`
Navigates to a URL in the browser.

```json
{
  "action": "navigate",
  "url": "http://localhost:3000/register"
}
```

#### `evaluate`
Runs JavaScript in the browser context. Can access `document`, `window`, and saved context from previous steps.

```json
{
  "action": "evaluate",
  "function": "async () => { return { value: document.querySelector('input').value }; }",
  "saveAs": "inputValue"
}
```

**Accessing saved context:**
```json
{
  "action": "evaluate",
  "function": "async (ctx) => { const email = ctx.previousStep.email; return { email }; }",
  "saveAs": "currentStep"
}
```

#### `assert`
Validates an expression using saved context.

```json
{
  "action": "assert",
  "expression": "inputValue.value === 'expected'"
}
```

## Debugging Failed Tests

### 1. Run Single Scenario with Verbose Output

```bash
docker compose -f docker-compose.server.yml exec mcp-runner \
  node /work/scripts/mcp_runner.mjs /work/scenarios/full_registration_e2e.json
```

### 2. Check Service Logs

```bash
# Backend logs
docker compose -f docker-compose.server.yml logs backend --tail=100

# Frontend logs
docker compose -f docker-compose.server.yml logs frontend --tail=100

# MCP runner logs
docker compose -f docker-compose.server.yml logs mcp-runner --tail=100
```

### 3. Take Screenshots in Scenarios

Add screenshot code to your scenario:

```json
{
  "action": "evaluate",
  "function": "async () => { const canvas = document.createElement('canvas'); const ctx = canvas.getContext('2d'); /* screenshot logic */ return { screenshot: 'base64data' }; }"
}
```

Or use the MCP runner's built-in screenshot for specific scenarios (see `mcp_runner.mjs` line 143).

### 4. Common Issues

#### React Forms Not Updating
React controlled forms require special handling. Use `nativeInputValueSetter`:

```javascript
function triggerReactInput(el, value) {
  const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
    window.HTMLInputElement.prototype, 'value'
  ).set;
  nativeInputValueSetter.call(el, value);
  el.dispatchEvent(new Event('input', { bubbles: true, composed: true }));
  el.dispatchEvent(new Event('change', { bubbles: true }));
}
```

#### Timeouts
Increase wait times in scenarios:

```javascript
await new Promise(r => setTimeout(r, 10000)); // Wait 10 seconds
```

#### Element Not Found
Use multiple selectors and fallbacks:

```javascript
const element = document.querySelector('selector1') || 
                document.querySelector('selector2') ||
                Array.from(document.querySelectorAll('selector3'))[0];
```

#### Navigation Issues
Check if navigation actually happened:

```javascript
const start = Date.now();
while (Date.now() - start < 30000) {
  if (window.location.pathname.includes('/expected')) {
    return { success: true };
  }
  await new Promise(r => setTimeout(r, 500));
}
```

## Creating New Scenarios

### Step 1: Create JSON File

Create `tests/mcp/scenarios/my_new_scenario.json`:

```json
{
  "name": "my-new-scenario",
  "description": "Tests my new feature",
  "steps": [
    {
      "action": "navigate",
      "url": "http://localhost:3000/my-page"
    },
    {
      "action": "evaluate",
      "function": "async () => { await new Promise(r => setTimeout(r, 2000)); return { loaded: true }; }",
      "saveAs": "pageLoad"
    },
    {
      "action": "assert",
      "expression": "pageLoad.loaded === true"
    }
  ]
}
```

### Step 2: Test Locally

```bash
./scripts/check-pwy /work/scenarios/my_new_scenario.json
```

### Step 3: Add to Test Suite

Edit `scripts/run-e2e-tests.sh` to include your scenario in the default list.

## CI/CD Integration

### GitHub Actions

The project includes two GitHub Actions workflows:

1. **`.github/workflows/e2e-tests.yml`** - Runs on push/PR (fast scenarios only)
2. **`.github/workflows/e2e-tests-full.yml`** - Runs daily (all scenarios)

### Required Secrets

Add these secrets to your GitHub repository:

- `OPENAI_API_KEY`
- `GEMINI_API_KEY`
- `GOOGLE_CLOUD_PROJECT_ID`

### Manual Trigger

```bash
# Trigger full suite manually
gh workflow run e2e-tests-full.yml

# Trigger with all scenarios option
gh workflow run e2e-tests.yml -f run_all_scenarios=true
```

## Best Practices

1. **Keep scenarios focused** - Each scenario should test one specific flow
2. **Use descriptive names** - Scenario names should clearly indicate what's being tested
3. **Add wait times** - React apps need time to render; add appropriate delays
4. **Handle async operations** - Use polling loops for dynamic content
5. **Save intermediate results** - Use `saveAs` to debug multi-step flows
6. **Make assertions specific** - Test specific conditions, not just "page loaded"
7. **Handle edge cases** - Test both success and failure paths

## Troubleshooting

### Services Not Starting

```bash
# Check service status
docker compose -f docker-compose.server.yml ps

# Restart services
docker compose -f docker-compose.server.yml restart

# Rebuild if needed
docker compose -f docker-compose.server.yml up -d --build
```

### Tests Timing Out

Increase timeout in `scripts/run-e2e-tests.sh`:

```bash
E2E_TIMEOUT=600 ./scripts/run-e2e-tests.sh
```

### Browser Not Launching

Check MCP runner container:

```bash
docker compose -f docker-compose.server.yml exec mcp-runner ls -la /work
docker compose -f docker-compose.server.yml exec mcp-runner node --version
```

### React Form Issues

See "React Forms Not Updating" section above. The `full_registration_e2e.json` scenario has a working example.

## Resources

- **MCP Runner**: `frontend/scripts/mcp_runner.mjs`
- **Scenarios**: `tests/mcp/scenarios/*.json`
- **Test Runner**: `scripts/run-e2e-tests.sh`
- **Playwright Config**: `frontend/playwright.config.ts`
