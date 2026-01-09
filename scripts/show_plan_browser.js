#!/usr/bin/env node
/**
 * Script to open browser and show learning plan after profile building
 */

const { chromium } = require('playwright');

async function showPlan() {
  const browser = await chromium.launch({ 
    headless: false, // Show browser
    slowMo: 1000 // Slow down for visibility
  });
  
  const context = await browser.newContext();
  const page = await context.newPage();
  
  try {
    // Navigate to home page (assuming user is logged in)
    console.log('Navigating to home page...');
    await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
    
    // Wait for page to load
    await page.waitForTimeout(2000);
    
    // Check if we need to login
    const loginButton = await page.locator('text=/login|sign in/i').first().isVisible().catch(() => false);
    if (loginButton) {
      console.log('Need to login. Please login manually in the browser.');
      console.log('After login, the page will check for the learning plan...');
      // Wait for user to login
      await page.waitForURL('**/', { timeout: 120000 });
    }
    
    // Wait for home status to load
    console.log('Waiting for home status to load...');
    await page.waitForTimeout(3000);
    
    // Check for learning path
    console.log('Checking for learning plan...');
    
    // Look for "Next Step" widget or learning path content
    const nextStepWidget = page.locator('text=/next step|learning path|your path/i').first();
    const buildingMessage = page.locator('text=/building|generating|please check back/i').first();
    
    const hasNextStep = await nextStepWidget.isVisible().catch(() => false);
    const hasBuilding = await buildingMessage.isVisible().catch(() => false);
    
    if (hasNextStep) {
      console.log('✅ Learning plan is displayed!');
      // Take a screenshot
      await page.screenshot({ path: '/tmp/learning_plan_displayed.png', fullPage: true });
      console.log('Screenshot saved to /tmp/learning_plan_displayed.png');
    } else if (hasBuilding) {
      console.log('⏳ Learning plan is being generated. Waiting up to 60 seconds...');
      // Poll for the plan to appear
      let found = false;
      for (let i = 0; i < 20; i++) {
        await page.waitForTimeout(3000);
        await page.reload({ waitUntil: 'networkidle' });
        const hasPlan = await nextStepWidget.isVisible().catch(() => false);
        if (hasPlan) {
          console.log('✅ Learning plan appeared!');
          await page.screenshot({ path: '/tmp/learning_plan_displayed.png', fullPage: true });
          console.log('Screenshot saved to /tmp/learning_plan_displayed.png');
          found = true;
          break;
        }
        console.log(`Still waiting... (${(i + 1) * 3} seconds)`);
      }
      if (!found) {
        console.log('⚠️  Learning plan did not appear within 60 seconds.');
        await page.screenshot({ path: '/tmp/learning_plan_still_building.png', fullPage: true });
        console.log('Screenshot saved to /tmp/learning_plan_still_building.png');
      }
    } else {
      console.log('⚠️  Could not find learning plan or building message.');
      await page.screenshot({ path: '/tmp/home_page.png', fullPage: true });
      console.log('Screenshot saved to /tmp/home_page.png');
    }
    
    // Keep browser open for 30 seconds so user can see
    console.log('\nBrowser will stay open for 30 seconds for you to inspect...');
    await page.waitForTimeout(30000);
    
  } catch (error) {
    console.error('Error:', error);
    await page.screenshot({ path: '/tmp/error_screenshot.png', fullPage: true });
  } finally {
    await browser.close();
  }
}

showPlan().catch(console.error);

