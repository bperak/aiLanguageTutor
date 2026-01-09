#!/usr/bin/env node
/**
 * Take a screenshot of the learning plan page
 */

const { chromium } = require('playwright');
const fs = require('fs');

async function takeScreenshot() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 }
  });
  const page = await context.newPage();
  
  try {
    console.log('Navigating to home page...');
    await page.goto('http://localhost:3000', { waitUntil: 'networkidle', timeout: 30000 });
    
    // Wait a bit for content to load
    await page.waitForTimeout(3000);
    
    // Check if we're on login page
    const isLoginPage = await page.locator('input[type="password"], button:has-text("Login"), button:has-text("Sign in")').first().isVisible().catch(() => false);
    
    if (isLoginPage) {
      console.log('Login page detected. Taking screenshot of login page...');
      await page.screenshot({ path: '/tmp/login_page.png', fullPage: true });
      console.log('Screenshot saved to /tmp/login_page.png');
      console.log('Please login manually, then run this script again.');
    } else {
      // Check for learning plan
      console.log('Checking for learning plan...');
      
      // Wait for either the plan or building message
      await page.waitForTimeout(5000);
      
      // Take screenshot
      const screenshotPath = '/tmp/learning_plan_page.png';
      await page.screenshot({ path: screenshotPath, fullPage: true });
      console.log(`Screenshot saved to ${screenshotPath}`);
      
      // Check what's on the page
      const bodyText = await page.textContent('body').catch(() => '');
      const hasPlan = /next step|learning path|your path/i.test(bodyText);
      const hasBuilding = /building|generating|please check back/i.test(bodyText);
      
      if (hasPlan) {
        console.log('✅ Learning plan is visible on the page!');
      } else if (hasBuilding) {
        console.log('⏳ Learning plan is being generated. The page will auto-update when ready.');
      } else {
        console.log('⚠️  Could not detect learning plan or building message.');
      }
      
      // Copy to host-accessible location
      if (fs.existsSync(screenshotPath)) {
        console.log(`\nScreenshot available at: ${screenshotPath}`);
        console.log('You can view it with: xdg-open /tmp/learning_plan_page.png');
      }
    }
    
  } catch (error) {
    console.error('Error:', error.message);
    await page.screenshot({ path: '/tmp/error_screenshot.png', fullPage: true });
    console.log('Error screenshot saved to /tmp/error_screenshot.png');
  } finally {
    await browser.close();
  }
}

takeScreenshot().catch(console.error);

