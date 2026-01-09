#!/usr/bin/env node
/**
 * E2E test with REAL-TIME browser preview
 * Creates a live HTTP server that streams screenshots as the test runs
 */

import { chromium } from 'playwright';
import http from 'http';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const PRODUCTION_URL = 'https://ailanguagetutor.syntagent.com';
const PORT = 8080;
const SCREENSHOT_DIR = '/tmp/e2e_live_screenshots';

// Ensure screenshot directory exists
if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

// Current test state
let currentScreenshot = null;
let testStatus = { step: 0, name: 'Starting...', description: '' };
let testLog = [];

function updateScreenshot(screenshotPath) {
  currentScreenshot = screenshotPath;
  // Copy to a fixed name for the web server
  if (fs.existsSync(screenshotPath)) {
    fs.copyFileSync(screenshotPath, path.join(SCREENSHOT_DIR, 'current.png'));
  }
}

function addLog(step, name, description) {
  testStatus = { step, name, description, timestamp: new Date().toISOString() };
  testLog.push(testStatus);
  if (testLog.length > 50) testLog.shift(); // Keep last 50 entries
}

// Create HTTP server for live preview
const server = http.createServer((req, res) => {
  if (req.url === '/' || req.url === '/index.html') {
    const html = `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>E2E Test - Live Browser View</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0e27;
            color: #fff;
            padding: 20px;
            overflow-x: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 20px;
            text-align: center;
        }
        .header h1 {
            font-size: 2em;
            margin-bottom: 10px;
        }
        .status {
            background: rgba(255,255,255,0.1);
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .status h2 {
            color: #667eea;
            margin-bottom: 10px;
        }
        .browser-view {
            background: #1a1f3a;
            border: 3px solid #667eea;
            border-radius: 12px;
            padding: 10px;
            margin-bottom: 20px;
            box-shadow: 0 0 30px rgba(102, 126, 234, 0.3);
        }
        .browser-view img {
            width: 100%;
            border-radius: 8px;
            display: block;
        }
        .log {
            background: #1a1f3a;
            border: 2px solid #2d3555;
            border-radius: 8px;
            padding: 15px;
            max-height: 300px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }
        .log-entry {
            padding: 5px 0;
            border-bottom: 1px solid #2d3555;
        }
        .log-entry:last-child {
            border-bottom: none;
        }
        .timestamp {
            color: #667eea;
            margin-right: 10px;
        }
        .auto-refresh {
            position: fixed;
            top: 10px;
            right: 10px;
            background: rgba(102, 126, 234, 0.8);
            padding: 10px 20px;
            border-radius: 20px;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="auto-refresh">🔄 Auto-refreshing every 0.5s</div>
    
    <div class="header">
        <h1>🚀 E2E Test - Live Browser View</h1>
        <p>${PRODUCTION_URL}</p>
    </div>
    
    <div class="status">
        <h2>Current Step: ${testStatus.step} - ${testStatus.name}</h2>
        <p>${testStatus.description}</p>
    </div>
    
    <div class="browser-view">
        <h3 style="margin-bottom: 10px; color: #667eea;">Live Browser Screenshot:</h3>
        ${currentScreenshot ? 
          `<img src="/screenshot?t=${Date.now()}" alt="Live browser view" id="liveScreenshot">` : 
          '<div style="padding: 100px; text-align: center; color: #4a5568;">Waiting for browser to start...</div>'
        }
    </div>
    
    <div class="log">
        <h3 style="margin-bottom: 10px; color: #667eea;">Test Log:</h3>
        ${testLog.map(entry => `
            <div class="log-entry">
                <span class="timestamp">[${new Date(entry.timestamp).toLocaleTimeString()}]</span>
                <strong>Step ${entry.step}:</strong> ${entry.name} - ${entry.description}
            </div>
        `).reverse().join('')}
    </div>
    
    <script>
        // Auto-refresh page every 500ms
        setInterval(() => {
            const img = document.getElementById('liveScreenshot');
            if (img) {
                img.src = '/screenshot?t=' + Date.now();
            }
            // Reload status
            fetch('/status')
                .then(r => r.json())
                .then(data => {
                    if (data.step !== ${testStatus.step}) {
                        location.reload();
                    }
                });
        }, 500);
        
        // Also refresh full page every 2 seconds to get latest HTML
        setTimeout(() => location.reload(), 2000);
    </script>
</body>
</html>`;
    
    res.writeHead(200, { 'Content-Type': 'text/html' });
    res.end(html);
  } else if (req.url.startsWith('/screenshot')) {
    const screenshotPath = path.join(SCREENSHOT_DIR, 'current.png');
    if (fs.existsSync(screenshotPath)) {
      const image = fs.readFileSync(screenshotPath);
      res.writeHead(200, { 
        'Content-Type': 'image/png',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
      });
      res.end(image);
    } else {
      res.writeHead(404);
      res.end('Screenshot not available');
    }
  } else if (req.url === '/status') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(testStatus));
  } else {
    res.writeHead(404);
    res.end('Not found');
  }
});

server.listen(PORT, () => {
  console.log(`\n🌐 Live browser preview server started!`);
  console.log(`📊 Open in browser: http://localhost:${PORT}`);
  console.log(`👀 The page will auto-refresh to show live test execution!\n`);
});

async function main() {
  const browser = await chromium.launch({ 
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 }
  });
  const page = await context.newPage();
  
  // Function to take and update screenshot
  const takeLiveScreenshot = async (stepName) => {
    const screenshotPath = path.join(SCREENSHOT_DIR, `step_${Date.now()}.png`);
    await page.screenshot({ path: screenshotPath, fullPage: true });
    updateScreenshot(screenshotPath);
    console.log(`   📸 Screenshot updated: ${stepName}`);
  };
  
  try {
    // Step 1
    addLog(1, 'Home Page', 'Navigating to production site...');
    console.log('\n[1] Navigating to home page...');
    await page.goto(PRODUCTION_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await takeLiveScreenshot('Home Page');
    await page.waitForTimeout(1000);
    
    // Step 2
    addLog(2, 'Register Page', 'Clicking register link...');
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
    await takeLiveScreenshot('Register Page');
    
    // Step 3
    addLog(3, 'Form Filled', 'Filling registration form...');
    console.log('\n[3] Filling registration form...');
    const timestamp = Date.now();
    const username = `e2etest_${timestamp}`;
    const email = `e2etest_${timestamp}@example.com`;
    await page.fill('input[type="email"], input[name="email"]', email);
    await page.fill('input[name="username"]', username);
    await page.fill('input[type="password"]', 'TestPass123');
    await page.waitForTimeout(500);
    await takeLiveScreenshot('Form Filled');
    
    // Step 4
    addLog(4, 'Registration', 'Submitting registration...');
    console.log('\n[4] Submitting registration...');
    await page.locator('button[type="submit"]').click();
    try {
      await page.waitForURL('**/profile/build**', { timeout: 15000 });
    } catch (e) {
      await page.waitForTimeout(5000);
    }
    await takeLiveScreenshot('Registration Complete');
    
    // Step 5
    addLog(5, 'Profile Building', 'Starting profile building...');
    console.log('\n[5] Starting profile building...');
    await page.waitForTimeout(3000);
    await takeLiveScreenshot('Profile Building');
    
    // Step 6
    addLog(6, 'Sending Message', 'Sending profile message...');
    console.log('\n[6] Sending profile messages...');
    const textarea = page.locator('textarea, input[type="text"]').first();
    if (await textarea.count() > 0) {
      await textarea.fill('I want to learn Japanese for travel. I have no prior experience.');
      await page.waitForTimeout(500);
      const sendBtn = page.locator('button:has-text("Send"), button[type="submit"]').first();
      if (await sendBtn.count() > 0 && !(await sendBtn.isDisabled())) {
        await sendBtn.click();
      } else {
        await textarea.press('Enter');
      }
      await page.waitForTimeout(3000);
      await takeLiveScreenshot('Message Sent');
    }
    
    // Step 7
    addLog(7, 'Completing Profile', 'Completing profile...');
    console.log('\n[7] Completing profile...');
    await page.waitForTimeout(3000);
    const completeBtn = page.locator('button:has-text("Complete"), button:has-text("Finish")');
    if (await completeBtn.count() > 0) {
      await completeBtn.first().click();
      await page.waitForTimeout(3000);
    }
    await takeLiveScreenshot('Profile Complete');
    
    // Step 8
    addLog(8, 'Checking Path', 'Checking for learning path...');
    console.log('\n[8] Checking for learning path...');
    await page.goto(`${PRODUCTION_URL}/`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(5000);
    
    for (let i = 0; i < 6; i++) {
      addLog(8 + i, `Path Check ${i + 1}`, 'Checking if learning path is visible...');
      await page.waitForTimeout(5000);
      await takeLiveScreenshot(`Path Check ${i + 1}`);
      const bodyText = (await page.textContent('body')).toLowerCase();
      if (bodyText.includes('next step') || bodyText.includes('learning path')) {
        if (!bodyText.includes('building in background')) {
          addLog(8 + i, 'Path Found!', 'Learning path is visible!');
          break;
        }
      }
    }
    
    addLog(99, 'Test Complete', 'E2E test finished!');
    console.log(`\n✅ Test complete! Browser preview available at: http://localhost:${PORT}`);
    console.log('   The server will keep running. Press Ctrl+C to stop.');
    
    // Keep server running
    await new Promise(() => {}); // Never resolves
    
  } catch (error) {
    console.error(`\n❌ ERROR: ${error.message}`);
    addLog(999, 'ERROR', error.message);
    await takeLiveScreenshot('Error');
  } finally {
    // Don't close browser - keep it running for preview
    // await browser.close();
  }
}

main().catch((e) => {
  console.error('Fatal error:', e);
  process.exit(1);
});

