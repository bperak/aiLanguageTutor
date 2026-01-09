#!/usr/bin/env node
/**
 * E2E test for production site with browser tab preview
 * Creates an HTML report that can be viewed in Cursor's browser preview
 */

import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const PRODUCTION_URL = 'https://ailanguagetutor.syntagent.com';
const DEBUG_LOG_PATH = '/home/benedikt/.cursor/debug.log';
const REPORT_DIR = '/tmp/e2e_browser_report';
const REPORT_HTML = path.join(REPORT_DIR, 'index.html');

// Ensure report directory exists
if (!fs.existsSync(REPORT_DIR)) {
  fs.mkdirSync(REPORT_DIR, { recursive: true });
}

// Test steps data
const testSteps = [];
let currentStep = 0;

function logDebug(sessionId, runId, hypothesisId, location, message, data) {
  try {
    const logDir = path.dirname(DEBUG_LOG_PATH);
    if (!fs.existsSync(logDir)) {
      fs.mkdirSync(logDir, { recursive: true });
    }
    fs.appendFileSync(DEBUG_LOG_PATH, JSON.stringify({
      sessionId,
      runId,
      hypothesisId,
      location,
      message,
      data,
      timestamp: Date.now()
    }) + '\n');
  } catch (e) {
    // Ignore
  }
}

function generateHTMLReport() {
  const html = `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="2">
    <title>E2E Test - Live Report</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0e27;
            color: #fff;
            padding: 20px;
        }
        .container {
            max-width: 1600px;
            margin: 0 auto;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 20px;
            text-align: center;
        }
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        .status {
            display: inline-block;
            padding: 10px 20px;
            background: rgba(255,255,255,0.2);
            border-radius: 20px;
            margin-top: 10px;
        }
        .steps {
            display: grid;
            gap: 20px;
        }
        .step {
            background: #1a1f3a;
            border: 2px solid #2d3555;
            border-radius: 12px;
            overflow: hidden;
            transition: all 0.3s;
        }
        .step.active {
            border-color: #667eea;
            box-shadow: 0 0 20px rgba(102, 126, 234, 0.5);
        }
        .step.completed {
            border-color: #10b981;
        }
        .step-header {
            background: linear-gradient(135deg, #2d3555 0%, #1a1f3a 100%);
            padding: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .step-number {
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }
        .step-name {
            font-size: 1.3em;
            font-weight: 600;
        }
        .step-content {
            padding: 20px;
        }
        .step-description {
            color: #a0aec0;
            margin-bottom: 15px;
        }
        .step-screenshot {
            width: 100%;
            border-radius: 8px;
            margin-top: 15px;
            border: 2px solid #2d3555;
        }
        .step-data {
            margin-top: 15px;
            padding: 15px;
            background: #0f1419;
            border-radius: 6px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            color: #a0aec0;
        }
        .progress-bar {
            width: 100%;
            height: 6px;
            background: #2d3555;
            border-radius: 3px;
            margin: 20px 0;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            transition: width 0.3s;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 E2E Test - Live Report</h1>
            <p>${PRODUCTION_URL}</p>
            <div class="status">
                ${testSteps.length > 0 ? `Step ${currentStep} of ${testSteps.length}` : 'Starting...'}
            </div>
        </div>
        
        <div class="progress-bar">
            <div class="progress-fill" style="width: ${testSteps.length > 0 ? (currentStep / testSteps.length * 100) : 0}%"></div>
        </div>
        
        <div class="steps">
            ${testSteps.map((step, idx) => `
                <div class="step ${idx === currentStep - 1 ? 'active' : ''} ${idx < currentStep - 1 ? 'completed' : ''}">
                    <div class="step-header">
                        <span class="step-number">#${step.step}</span>
                        <span class="step-name">${step.name}</span>
                    </div>
                    <div class="step-content">
                        <div class="step-description">${step.description}</div>
                        ${step.screenshot ? `
                            <img src="${step.screenshot}" alt="${step.name}" class="step-screenshot">
                        ` : '<div style="padding: 40px; text-align: center; color: #4a5568;">Waiting for screenshot...</div>'}
                        ${Object.keys(step.data).length > 0 ? `
                            <div class="step-data">
                                <pre>${JSON.stringify(step.data, null, 2)}</pre>
                            </div>
                        ` : ''}
                    </div>
                </div>
            `).join('')}
        </div>
    </div>
</body>
</html>`;
  
  fs.writeFileSync(REPORT_HTML, html);
  return REPORT_HTML;
}

async function addStep(name, description, screenshotPath = null, data = {}) {
  currentStep++;
  const step = {
    step: currentStep,
    name,
    description,
    screenshot: screenshotPath ? `file://${screenshotPath}` : null,
    timestamp: new Date().toISOString(),
    data
  };
  testSteps.push(step);
  generateHTMLReport();
  console.log(`   ✅ Step ${currentStep}: ${name}`);
}

async function main() {
  const runId = `prod-e2e-${Date.now()}`;
  const sessionId = 'debug-session';
  
  console.log('='.repeat(80));
  console.log('PRODUCTION E2E TEST - Browser Preview Mode');
  console.log(`Testing: ${PRODUCTION_URL}`);
  console.log(`📊 HTML Report: ${REPORT_HTML}`);
  console.log('👀 Open the HTML file in Cursor\'s browser preview to watch the test!');
  console.log('='.repeat(80));
  
  // Generate initial report
  generateHTMLReport();
  console.log(`\n✅ Initial report created. Open: ${REPORT_HTML}`);
  console.log('   (This page auto-refreshes every 2 seconds)\n');
  
  const browser = await chromium.launch({ 
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 }
  });
  const page = await context.newPage();
  
  try {
    // Step 1: Navigate
    console.log('\n[1] Navigating to home page...');
    const navStart = Date.now();
    await page.goto(PRODUCTION_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    const navDuration = Date.now() - navStart;
    const screenshot1 = path.join(REPORT_DIR, 'step_01_home.png');
    await page.screenshot({ path: screenshot1, fullPage: true });
    await addStep('Home Page', 'Navigated to production home page', screenshot1, { duration_ms: navDuration });
    await page.waitForTimeout(2000);
    
    // Step 2: Register
    console.log('\n[2] Clicking register link...');
    try {
      const registerLink = page.locator('a[href="/register"], a:has-text("Get started")').first();
      if (await registerLink.count() > 0) {
        await registerLink.click();
        await page.waitForTimeout(2000);
      } else {
        await page.goto(`${PRODUCTION_URL}/register`, { waitUntil: 'domcontentloaded' });
      }
    } catch (e) {
      await page.goto(`${PRODUCTION_URL}/register`, { waitUntil: 'domcontentloaded' });
    }
    const screenshot2 = path.join(REPORT_DIR, 'step_02_register.png');
    await page.screenshot({ path: screenshot2, fullPage: true });
    await addStep('Register Page', 'Navigated to registration page', screenshot2, { url: page.url() });
    
    // Step 3: Fill form
    console.log('\n[3] Filling registration form...');
    const timestamp = Date.now();
    const username = `e2etest_${timestamp}`;
    const email = `e2etest_${timestamp}@example.com`;
    const password = 'TestPass123';
    
    await page.fill('input[type="email"], input[name="email"]', email);
    await page.fill('input[name="username"]', username);
    await page.fill('input[type="password"]', password);
    await page.waitForTimeout(1000);
    const screenshot3 = path.join(REPORT_DIR, 'step_03_form_filled.png');
    await page.screenshot({ path: screenshot3, fullPage: true });
    await addStep('Form Filled', 'Registration form filled', screenshot3, { username, email });
    
    // Step 4: Submit
    console.log('\n[4] Submitting registration...');
    const submitStart = Date.now();
    await page.locator('button[type="submit"]').click();
    try {
      await page.waitForURL('**/profile/build**', { timeout: 15000 });
    } catch (e) {
      await page.waitForTimeout(5000);
    }
    const submitDuration = Date.now() - submitStart;
    const screenshot4 = path.join(REPORT_DIR, 'step_04_registered.png');
    await page.screenshot({ path: screenshot4, fullPage: true });
    await addStep('Registration Complete', 'User registered and redirected', screenshot4, { duration_ms: submitDuration, url: page.url() });
    
    // Step 5: Profile building
    console.log('\n[5] Starting profile building...');
    await page.waitForTimeout(3000);
    const screenshot5 = path.join(REPORT_DIR, 'step_05_profile_start.png');
    await page.screenshot({ path: screenshot5, fullPage: true });
    await addStep('Profile Building', 'On profile building page', screenshot5, { url: page.url() });
    
    // Step 6: Send messages
    console.log('\n[6] Sending profile messages...');
    const textarea = page.locator('textarea, input[type="text"]').first();
    if (await textarea.count() > 0) {
      await textarea.fill('I want to learn Japanese for travel. I have no prior experience.');
      await page.waitForTimeout(500);
      const sendBtn = page.locator('button:has-text("Send"), button[type="submit"]').first();
      if (await sendBtn.count() > 0 && !(await sendBtn.isDisabled())) {
        await sendBtn.click();
        await page.waitForTimeout(3000);
      } else {
        await textarea.press('Enter');
        await page.waitForTimeout(3000);
      }
      const screenshot6 = path.join(REPORT_DIR, 'step_06_message_sent.png');
      await page.screenshot({ path: screenshot6, fullPage: true });
      await addStep('Message Sent', 'First profile message sent', screenshot6);
    }
    
    // Step 7: Complete profile
    console.log('\n[7] Completing profile...');
    await page.waitForTimeout(3000);
    const completeBtn = page.locator('button:has-text("Complete"), button:has-text("Finish")');
    if (await completeBtn.count() > 0) {
      await completeBtn.first().click();
      await page.waitForTimeout(3000);
    }
    const screenshot7 = path.join(REPORT_DIR, 'step_07_complete.png');
    await page.screenshot({ path: screenshot7, fullPage: true });
    await addStep('Profile Complete', 'Profile completion clicked', screenshot7);
    
    // Step 8: Check learning path
    console.log('\n[8] Checking for learning path...');
    await page.goto(`${PRODUCTION_URL}/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(5000);
    
    for (let i = 0; i < 6; i++) {
      await page.waitForTimeout(5000);
      const bodyText = (await page.textContent('body')).toLowerCase();
      const hasPath = bodyText.includes('next step') || bodyText.includes('learning path');
      const hasBuilding = bodyText.includes('building in background');
      
      const screenshot8 = path.join(REPORT_DIR, `step_08_check_${i + 1}.png`);
      await page.screenshot({ path: screenshot8, fullPage: true });
      await addStep(`Path Check ${i + 1}`, hasPath ? 'Learning path found!' : hasBuilding ? 'Path still generating...' : 'Waiting for path...', screenshot8, { has_path: hasPath, has_building: hasBuilding });
      
      if (hasPath && !hasBuilding) break;
    }
    
    // Final report
    generateHTMLReport();
    console.log(`\n✅ Test complete! Final report: ${REPORT_HTML}`);
    console.log('👀 Open the HTML file in Cursor\'s browser preview to see all steps!');
    
  } catch (error) {
    console.error(`\n❌ ERROR: ${error.message}`);
    const errorScreenshot = path.join(REPORT_DIR, 'error.png');
    await page.screenshot({ path: errorScreenshot, fullPage: true });
    await addStep('ERROR', error.message, errorScreenshot, { error: error.stack });
    generateHTMLReport();
  } finally {
    await browser.close();
  }
}

// Clear log
if (fs.existsSync(DEBUG_LOG_PATH)) {
  fs.unlinkSync(DEBUG_LOG_PATH);
}

main().catch((e) => {
  console.error('Fatal error:', e);
  process.exit(1);
});

