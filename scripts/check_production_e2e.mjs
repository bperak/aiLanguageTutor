#!/usr/bin/env node
/**
 * E2E test for production site: Register, complete profile, verify learning path
 * Uses Playwright to test the full flow in browser
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
    // Ignore log errors
  }
}

async function main() {
  const runId = `prod-e2e-${Date.now()}`;
  const sessionId = 'debug-session';
  
  console.log('='.repeat(80));
  console.log('PRODUCTION E2E TEST: Register -> Profile -> Learning Path');
  console.log(`Testing: ${PRODUCTION_URL}`);
  console.log('='.repeat(80));
  
  // Launch browser - try visible mode first, fall back to headless with screenshots
  let browser, context, page;
  try {
    browser = await chromium.launch({ 
      headless: false,
      slowMo: 300, // Slow down actions so user can see what's happening
      args: ['--start-maximized']
    });
    console.log('   ✅ Browser launched in visible mode');
  } catch (e) {
    console.log('   ⚠️  Cannot launch visible browser (no display), using headless with screenshots');
    browser = await chromium.launch({ 
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
  }
  
  context = await browser.newContext({
    viewport: { width: 1920, height: 1080 }
  });
  page = await context.newPage();
  
  // Store screenshots and test data for HTML report
  const testSteps = [];
  const screenshotsDir = '/tmp/e2e_screenshots';
  const fs = await import('fs');
  const path = await import('path');
  
  // Create screenshots directory
  if (!fs.existsSync(screenshotsDir)) {
    fs.mkdirSync(screenshotsDir, { recursive: true });
  }
  
  // Helper to take step screenshots and record step info
  const takeStepScreenshot = async (stepName, stepNumber, description, data = {}) => {
    const screenshotPath = path.join(screenshotsDir, `step_${stepNumber.toString().padStart(2, '0')}_${stepName.replace(/\s+/g, '_')}.png`);
    await page.screenshot({ path: screenshotPath, fullPage: true });
    const relativePath = screenshotPath.replace('/tmp/', '');
    testSteps.push({
      step: stepNumber,
      name: stepName,
      description,
      screenshot: relativePath,
      timestamp: new Date().toISOString(),
      data
    });
    console.log(`   📸 Screenshot: ${screenshotPath}`);
    return screenshotPath;
  };
  
  // Function to generate HTML report
  const generateHTMLReport = () => {
    const html = `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>E2E Test Report - Production Site</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            color: #333;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        .header p {
            opacity: 0.9;
            font-size: 1.1em;
        }
        .summary {
            padding: 30px;
            background: #f8f9fa;
            border-bottom: 2px solid #e9ecef;
        }
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .summary-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .summary-card h3 {
            color: #667eea;
            margin-bottom: 10px;
        }
        .summary-card .value {
            font-size: 2em;
            font-weight: bold;
            color: #333;
        }
        .steps {
            padding: 30px;
        }
        .step {
            margin-bottom: 40px;
            border: 2px solid #e9ecef;
            border-radius: 12px;
            overflow: hidden;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .step:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(0,0,0,0.15);
        }
        .step-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .step-number {
            font-size: 2em;
            font-weight: bold;
            opacity: 0.8;
        }
        .step-name {
            font-size: 1.5em;
            font-weight: 600;
        }
        .step-content {
            padding: 20px;
        }
        .step-description {
            color: #666;
            margin-bottom: 20px;
            font-size: 1.1em;
        }
        .step-screenshot {
            width: 100%;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            margin-top: 15px;
            cursor: pointer;
            transition: transform 0.2s;
        }
        .step-screenshot:hover {
            transform: scale(1.02);
        }
        .step-data {
            margin-top: 15px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 6px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }
        .status-badge {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 0.9em;
        }
        .status-success { background: #d4edda; color: #155724; }
        .status-warning { background: #fff3cd; color: #856404; }
        .status-error { background: #f8d7da; color: #721c24; }
        .footer {
            padding: 30px;
            text-align: center;
            background: #f8f9fa;
            color: #666;
        }
        @media (max-width: 768px) {
            .header h1 { font-size: 1.8em; }
            .step-header { flex-direction: column; text-align: center; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 E2E Test Report</h1>
            <p>Production Site: ${PRODUCTION_URL}</p>
            <p>Test Run: ${new Date().toLocaleString()}</p>
        </div>
        
        <div class="summary">
            <h2>Test Summary</h2>
            <div class="summary-grid">
                <div class="summary-card">
                    <h3>Total Steps</h3>
                    <div class="value">${testSteps.length}</div>
                </div>
                <div class="summary-card">
                    <h3>Status</h3>
                    <div class="value">${testSteps.length > 0 ? '✅ Running' : '⏳ Starting'}</div>
                </div>
                <div class="summary-card">
                    <h3>Screenshots</h3>
                    <div class="value">${testSteps.length}</div>
                </div>
            </div>
        </div>
        
        <div class="steps">
            <h2 style="margin-bottom: 20px;">Test Steps</h2>
            ${testSteps.map(step => `
                <div class="step">
                    <div class="step-header">
                        <span class="step-number">#${step.step}</span>
                        <span class="step-name">${step.name}</span>
                    </div>
                    <div class="step-content">
                        <div class="step-description">${step.description}</div>
                        ${step.screenshot ? `
                            <img src="file://${path.join(screenshotsDir, step.screenshot)}" 
                                 alt="${step.name}" 
                                 class="step-screenshot"
                                 onclick="window.open(this.src, '_blank')">
                        ` : ''}
                        ${Object.keys(step.data).length > 0 ? `
                            <div class="step-data">
                                <strong>Data:</strong><br>
                                ${JSON.stringify(step.data, null, 2)}
                            </div>
                        ` : ''}
                        <div style="margin-top: 10px; color: #666; font-size: 0.9em;">
                            ⏰ ${new Date(step.timestamp).toLocaleTimeString()}
                        </div>
                    </div>
                </div>
            `).join('')}
        </div>
        
        <div class="footer">
            <p>Generated by Playwright E2E Test</p>
            <p>Screenshots saved in: ${screenshotsDir}</p>
        </div>
    </div>
</body>
</html>`;
    
    const reportPath = '/tmp/e2e_test_report.html';
    fs.writeFileSync(reportPath, html);
    return reportPath;
  };
  
  try {
    // Step 1: Navigate to home page
    console.log('\n[1] Navigating to home page...');
    console.log('   👀 Screenshots will be captured and shown in HTML report!');
    logDebug(sessionId, runId, 'E2E1', 'check_production_e2e.mjs', 'Navigate to home', {});
    const navStart = Date.now();
    await page.goto(PRODUCTION_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    const navDuration = Date.now() - navStart;
    logDebug(sessionId, runId, 'E2E1', 'check_production_e2e.mjs', 'Home page loaded', { duration_ms: navDuration });
    console.log(`   ✅ Loaded in ${navDuration}ms`);
    await page.waitForTimeout(2000);
    await takeStepScreenshot('Home Page', 1, 'Navigated to production home page', { duration_ms: navDuration, url: PRODUCTION_URL });
    
    // Step 2: Click register link
    console.log('\n[2] Clicking register link...');
    try {
      const registerLink = page.locator('a[href="/register"], a:has-text("Get started")').first();
      if (await registerLink.count() > 0) {
        await registerLink.click();
        await page.waitForTimeout(2000);
        console.log('   ✅ Clicked register link');
      } else {
        console.log('   Register link not found, navigating directly');
        await page.goto(`${PRODUCTION_URL}/register`, { waitUntil: 'domcontentloaded' });
      }
    } catch (e) {
      console.log('   Direct navigation to register page');
      await page.goto(`${PRODUCTION_URL}/register`, { waitUntil: 'domcontentloaded' });
    }
    await takeStepScreenshot('Register Page', 2, 'Navigated to registration page', { url: page.url() });
    
    // Step 3: Fill registration form
    console.log('\n[3] Filling registration form...');
    const timestamp = Date.now();
    const username = `e2etest_${timestamp}`;
    const email = `e2etest_${timestamp}@example.com`;
    const password = 'TestPass123';
    
    await page.fill('input[type="email"], input[name="email"]', email);
    await page.fill('input[name="username"]', username);
    await page.fill('input[type="password"]', password);
    await page.waitForTimeout(1000);
    console.log(`   Filled form: ${username}`);
    await takeStepScreenshot('Form Filled', 3, 'Registration form filled with test credentials', { username, email });
    
    // Step 4: Submit registration
    console.log('\n[4] Submitting registration...');
    const submitStart = Date.now();
    logDebug(sessionId, runId, 'E2E2', 'check_production_e2e.mjs', 'Registration submitted', { username, timestamp });
    
    const submitButton = page.locator('button[type="submit"]');
    await submitButton.click();
    
    // Wait for redirect to profile building
    try {
      await page.waitForURL('**/profile/build**', { timeout: 15000 });
      const submitDuration = Date.now() - submitStart;
      console.log(`   Registration completed in ${submitDuration}ms`);
      console.log(`   Redirected to: ${page.url()}`);
    } catch (e) {
      console.log(`   ⚠️  Waiting for redirect... Current URL: ${page.url()}`);
      await page.waitForTimeout(5000);
    }
    
    // Step 5: Start profile building session
    console.log('\n[5] Starting profile building session...');
    await page.waitForTimeout(3000);
    
    // Check current page state
    const profileUrl = page.url();
    const pageBodyText = (await page.textContent('body')).toLowerCase();
    console.log(`   Current URL: ${profileUrl}`);
    console.log(`   Page has chat: ${pageBodyText.includes('chat') || pageBodyText.includes('message')}`);
    
    // Look for start button or check if chat is already available
    const startButton = page.locator('button:has-text("Start"), button:has-text("Begin"), button:has-text("Create")');
    if (await startButton.count() > 0) {
      await startButton.first().click();
      await page.waitForTimeout(3000);
      console.log('   Started session');
    }
    
    // Step 6: Send profile messages
    console.log('\n[6] Sending profile messages...');
    await page.waitForTimeout(2000);
    
    // Try multiple selectors for textarea
    let textarea = null;
    const textareaSelectors = [
      'textarea',
      'input[type="text"]',
      '[contenteditable="true"]',
      '[role="textbox"]'
    ];
    
    for (const selector of textareaSelectors) {
      const el = page.locator(selector).first();
      if (await el.count() > 0) {
        textarea = el;
        console.log(`   Found textarea with selector: ${selector}`);
        break;
      }
    }
    
    if (textarea) {
      // Send first message
      await textarea.fill('I want to learn Japanese for travel. I have no prior experience.');
      await page.waitForTimeout(1000);
      
      // Find send button
      const sendButtonSelectors = [
        'button:has-text("Send")',
        'button[type="submit"]',
        'button:has-text("Submit")',
        'button[aria-label*="Send"]'
      ];
      
      let sendButton = null;
      for (const selector of sendButtonSelectors) {
        const btn = page.locator(selector).first();
        if (await btn.count() > 0 && !(await btn.isDisabled())) {
          sendButton = btn;
          break;
        }
      }
      
      if (sendButton) {
        await sendButton.click();
        await page.waitForTimeout(5000);
        console.log('   Sent first message');
      } else {
        // Try pressing Enter
        await textarea.press('Enter');
        await page.waitForTimeout(5000);
        console.log('   Sent first message (via Enter)');
      }
      
      // Send second message
      await textarea.fill('I prefer interactive learning with conversations. I can study 30 minutes per day.');
      await page.waitForTimeout(1000);
      
      if (sendButton && !(await sendButton.isDisabled())) {
        await sendButton.click();
        await page.waitForTimeout(5000);
        console.log('   Sent second message');
      } else {
        await textarea.press('Enter');
        await page.waitForTimeout(5000);
        console.log('   Sent second message (via Enter)');
      }
    } else {
      console.log('   ⚠️  Textarea not found, trying to find complete button directly');
    }
    
    // Step 7: Complete profile
    console.log('\n[7] Completing profile...');
    await page.waitForTimeout(3000);
    
    // Wait for complete button to appear (it might take time after messages)
    for (let i = 0; i < 10; i++) {
      const completeButton = page.locator('button:has-text("Complete"), button:has-text("Finish"), button:has-text("Done")');
      if (await completeButton.count() > 0) {
        const btn = completeButton.first();
        if (!(await btn.isDisabled())) {
          await btn.click();
          await page.waitForTimeout(3000);
          console.log('   Clicked complete button');
          break;
        }
      }
      await page.waitForTimeout(2000);
      console.log(`   Waiting for complete button... (attempt ${i + 1})`);
    }
    
    // Navigate to home page to check for learning path
    console.log('\n[7.5] Navigating to home page...');
    await page.waitForTimeout(2000);
    const beforeNavUrl = page.url();
    console.log(`   Current URL before nav: ${beforeNavUrl}`);
    
    // Force navigation to home
    await page.goto(`${PRODUCTION_URL}/`, { waitUntil: 'domcontentloaded', timeout: 15000 });
    await page.waitForTimeout(3000);
    const homeUrl = page.url();
    console.log(`   Navigated to: ${homeUrl}`);
    
    // Step 8: Check for learning path (with polling)
    console.log('\n[8] Checking for learning path...');
    console.log(`   Current URL: ${homeUrl}`);
    await page.waitForTimeout(5000);
    
    let pathFound = false;
    for (let i = 0; i < 6; i++) {
      await page.waitForTimeout(5000);
      const bodyText = (await page.textContent('body')).toLowerCase();
      const hasPath = bodyText.includes('next step') || bodyText.includes('learning path') || bodyText.includes('your path');
      const hasBuilding = bodyText.includes('building in background') || bodyText.includes('generating');
      
      logDebug(sessionId, runId, 'E2E3', 'check_production_e2e.mjs', `Path check ${i + 1}`, {
        has_path: hasPath,
        has_building: hasBuilding,
        url: page.url()
      });
      
      if (hasPath && !hasBuilding) {
        pathFound = true;
        console.log(`   ✅ Learning path found! (check ${i + 1})`);
        break;
      } else if (hasBuilding) {
        console.log(`   ⏳ Path still generating... (check ${i + 1})`);
      } else {
        console.log(`   ⏳ Waiting for path... (check ${i + 1})`);
      }
    }
    
    // Step 9: Final screenshot and generate HTML report
    console.log('\n[9] Taking final screenshot and generating report...');
    await takeStepScreenshot('Final State', 9, 'Final page state after learning path check', finalCheck);
    
    // Generate HTML report
    const reportPath = generateHTMLReport();
    console.log(`\n   📊 HTML Report generated: ${reportPath}`);
    console.log(`   👀 Open this file in Cursor's embedded browser to see the test results!`);
    
    // Final check
    const bodyText = (await page.textContent('body')).toLowerCase();
    const finalCheck = {
      url: page.url(),
      has_path: bodyText.includes('next step') || bodyText.includes('learning path'),
      has_building: bodyText.includes('building in background'),
      path_visible: (bodyText.includes('next step') || bodyText.includes('learning path')) && !bodyText.includes('building'),
      text_preview: bodyText.substring(0, 300)
    };
    
    logDebug(sessionId, runId, 'E2E4', 'check_production_e2e.mjs', 'E2E test completed', finalCheck);
    
    // Summary
    console.log('\n' + '='.repeat(80));
    console.log('E2E TEST SUMMARY');
    console.log('='.repeat(80));
    console.log(`URL: ${finalCheck.url}`);
    console.log(`Learning Path Found: ${finalCheck.has_path}`);
    console.log(`Path Visible (not building): ${finalCheck.path_visible}`);
    if (finalCheck.path_visible) {
      console.log('✅ SUCCESS: Learning path is visible!');
    } else if (finalCheck.has_building) {
      console.log('⚠️  Learning path is still being generated');
    } else {
      console.log('❌ Learning path not found');
    }
    
    console.log(`\n   ✅ Test complete! Open ${reportPath} in Cursor's embedded browser to view results.`);
    console.log(`   📸 All screenshots saved in: ${screenshotsDir}`);
    process.exit(finalCheck.path_visible ? 0 : 1);
    
  } catch (error) {
    console.error(`\n❌ ERROR: ${error.message}`);
    console.error(error.stack);
    
    // Take error screenshot
    try {
      await page.screenshot({ path: '/tmp/production_e2e_path_error.png', fullPage: true });
      console.log('Error screenshot saved: /tmp/production_e2e_path_error.png');
    } catch (e) {
      // Ignore
    }
    
    process.exit(1);
  } finally {
    await browser.close();
  }
}

// Clear log file
if (fs.existsSync(DEBUG_LOG_PATH)) {
  fs.unlinkSync(DEBUG_LOG_PATH);
  console.log(`Cleared debug log: ${DEBUG_LOG_PATH}`);
}

main().catch((e) => {
  console.error('Fatal error:', e);
  process.exit(1);
});

