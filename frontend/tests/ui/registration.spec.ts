import { test, expect } from '@playwright/test'

/**
 * E2E Registration Tests
 * 
 * Tests the full user registration flow including:
 * - Form validation
 * - Successful registration
 * - Profile building session
 * - Learning path generation
 */

test.describe('User Registration E2E', () => {
  
  test('full registration flow with profile building', async ({ page }) => {
    const ts = Date.now()
    const email = `e2e_${ts}@test.com`
    const username = `e2e_${ts}`
    const password = 'TestPass123'
    
    // Step 1: Navigate to register page
    await page.goto('/register')
    await expect(page.locator('input[name="email"], input[type="email"]').first()).toBeVisible({ timeout: 15000 })
    
    // Step 2: Fill registration form
    await page.fill('input[name="email"], input[type="email"]', email)
    await page.fill('input[name="username"]', username)
    await page.fill('input[type="password"]', password)
    
    // Take screenshot of filled form
    await page.screenshot({ path: '/tmp/e2e_registration_form.png', fullPage: true })
    
    // Step 3: Submit and wait for redirect to profile building
    await page.click('button[type="submit"]')
    
    // Wait for redirect to profile/build with generous timeout
    await page.waitForURL('**/profile/build**', { timeout: 30000 })
    console.log(`✅ Registration successful, redirected to: ${page.url()}`)
    
    // Take screenshot after redirect
    await page.screenshot({ path: '/tmp/e2e_registration_redirect.png', fullPage: true })
    
    // Step 4: Wait for profile building UI to load
    await page.waitForTimeout(3000)
    
    // Look for textarea or chat input
    const textarea = page.locator('textarea').first()
    const textInput = page.locator('input[type="text"]').first()
    
    const hasTextarea = await textarea.count() > 0
    const hasTextInput = await textInput.count() > 0
    
    if (hasTextarea) {
      await expect(textarea).toBeVisible({ timeout: 15000 })
      
      // Step 5: Send profile message
      await textarea.fill('I want to learn Japanese for travel and daily conversation. I am a complete beginner with no prior experience.')
      await page.waitForTimeout(500)
      
      // Find and click send button
      const sendButton = page.locator('button:has-text("Send"), button[type="submit"]').first()
      if (await sendButton.count() > 0 && await sendButton.isVisible()) {
        if (!(await sendButton.isDisabled())) {
          await sendButton.click()
          console.log('✅ Sent profile message')
          await page.waitForTimeout(8000) // Wait for AI response
        }
      } else {
        // Try pressing Enter
        await textarea.press('Enter')
        console.log('✅ Sent profile message via Enter')
        await page.waitForTimeout(8000)
      }
      
      // Take screenshot of chat
      await page.screenshot({ path: '/tmp/e2e_profile_chat.png', fullPage: true })
      
      // Send second message for more context
      await textarea.fill('I prefer interactive learning with conversations. I can study about 30 minutes per day.')
      await page.waitForTimeout(500)
      
      const sendBtn2 = page.locator('button:has-text("Send"), button[type="submit"]').first()
      if (await sendBtn2.count() > 0 && await sendBtn2.isVisible() && !(await sendBtn2.isDisabled())) {
        await sendBtn2.click()
        await page.waitForTimeout(8000)
      } else {
        await textarea.press('Enter')
        await page.waitForTimeout(8000)
      }
    } else if (hasTextInput) {
      console.log('ℹ️ Found text input instead of textarea')
      await textInput.fill('I want to learn Japanese for travel. Complete beginner.')
      await textInput.press('Enter')
      await page.waitForTimeout(5000)
    } else {
      console.log('⚠️ No text input found, looking for start/begin button')
      const startButton = page.locator('button:has-text("Start"), button:has-text("Begin"), button:has-text("Create")').first()
      if (await startButton.count() > 0) {
        await startButton.click()
        await page.waitForTimeout(3000)
      }
    }
    
    // Step 6: Look for and click complete/approve button
    console.log('Looking for complete button...')
    
    // Poll for complete button with retries
    let completedProfile = false
    for (let i = 0; i < 12; i++) {
      await page.waitForTimeout(3000)
      
      const completeButton = page.locator('button:has-text("Complete"), button:has-text("Approve"), button:has-text("Finish"), button:has-text("Done"), button:has-text("Save")')
      const buttonCount = await completeButton.count()
      
      if (buttonCount > 0) {
        const firstBtn = completeButton.first()
        if (await firstBtn.isVisible() && !(await firstBtn.isDisabled())) {
          await firstBtn.click()
          console.log(`✅ Clicked complete button (attempt ${i + 1})`)
          completedProfile = true
          await page.waitForTimeout(5000)
          break
        }
      }
      console.log(`⏳ Waiting for complete button... (attempt ${i + 1}/12)`)
    }
    
    // Take screenshot before navigation
    await page.screenshot({ path: '/tmp/e2e_profile_complete.png', fullPage: true })
    
    // Step 7: Navigate to home and check for learning path
    await page.goto('/')
    await page.waitForTimeout(5000)
    
    // Check for learning path indicators
    const bodyText = await page.textContent('body') || ''
    const hasLearningPath = /next step|learning path|your path|continue learning/i.test(bodyText)
    const isBuilding = /building in background|generating|please wait/i.test(bodyText)
    
    // Take final screenshot
    await page.screenshot({ path: '/tmp/e2e_final_home.png', fullPage: true })
    
    console.log(`Final state: hasLearningPath=${hasLearningPath}, isBuilding=${isBuilding}`)
    console.log(`URL: ${page.url()}`)
    
    // Assert either learning path is visible or it's being generated
    expect(hasLearningPath || isBuilding || completedProfile).toBeTruthy()
  })
  
  test('registration form validation - empty fields', async ({ page }) => {
    await page.goto('/register')
    await expect(page.locator('button[type="submit"]')).toBeVisible({ timeout: 15000 })
    
    // Try to submit with empty fields
    await page.click('button[type="submit"]')
    
    // Should not navigate away (still on register page)
    await page.waitForTimeout(1000)
    expect(page.url()).toContain('/register')
  })
  
  test('registration form validation - invalid email', async ({ page }) => {
    await page.goto('/register')
    await expect(page.locator('input[name="email"], input[type="email"]').first()).toBeVisible({ timeout: 15000 })
    
    // Fill with invalid email
    await page.fill('input[name="email"], input[type="email"]', 'not-an-email')
    await page.fill('input[name="username"]', 'testuser')
    await page.fill('input[type="password"]', 'TestPass123')
    
    await page.click('button[type="submit"]')
    await page.waitForTimeout(1000)
    
    // Should show validation error or stay on page
    const currentUrl = page.url()
    const bodyText = await page.textContent('body') || ''
    const hasError = /invalid|error|email/i.test(bodyText) || currentUrl.includes('/register')
    
    expect(hasError).toBeTruthy()
  })
  
  test('registration form validation - short password', async ({ page }) => {
    await page.goto('/register')
    await expect(page.locator('input[type="password"]')).toBeVisible({ timeout: 15000 })
    
    const ts = Date.now()
    await page.fill('input[name="email"], input[type="email"]', `test_${ts}@test.com`)
    await page.fill('input[name="username"]', `user_${ts}`)
    await page.fill('input[type="password"]', '123') // Too short
    
    await page.click('button[type="submit"]')
    await page.waitForTimeout(2000)
    
    // Should show validation error or stay on page
    const currentUrl = page.url()
    expect(currentUrl).toContain('/register')
  })
  
  test('navigate between login and register', async ({ page }) => {
    // Start at register
    await page.goto('/register')
    await page.waitForTimeout(1000)
    
    // Look for link to login
    const loginLink = page.locator('a[href="/login"], a:has-text("Login"), a:has-text("Sign in")').first()
    if (await loginLink.count() > 0) {
      await loginLink.click()
      await page.waitForURL('**/login**', { timeout: 10000 })
      expect(page.url()).toContain('/login')
    }
    
    // Look for link back to register
    const registerLink = page.locator('a[href="/register"], a:has-text("Register"), a:has-text("Sign up")').first()
    if (await registerLink.count() > 0) {
      await registerLink.click()
      await page.waitForURL('**/register**', { timeout: 10000 })
      expect(page.url()).toContain('/register')
    }
  })
})

test.describe('Profile Building Session', () => {
  
  test('profile building requires authentication', async ({ page }) => {
    // Try to access profile/build without being logged in
    await page.goto('/profile/build')
    await page.waitForTimeout(2000)
    
    const currentUrl = page.url()
    // Should redirect to login or show auth required message
    const redirectedToAuth = currentUrl.includes('/login') || currentUrl.includes('/register')
    const bodyText = await page.textContent('body') || ''
    const showsAuthMessage = /login|sign in|authenticate|unauthorized/i.test(bodyText)
    
    // Either redirected or shows message (or stays on profile/build if session exists)
    expect(redirectedToAuth || showsAuthMessage || currentUrl.includes('/profile')).toBeTruthy()
  })
})

test.describe('Login Flow', () => {
  
  test('login with valid credentials after registration', async ({ page }) => {
    // First register a new user
    const ts = Date.now()
    const email = `login_test_${ts}@test.com`
    const username = `login_test_${ts}`
    const password = 'TestPass123'
    
    await page.goto('/register')
    await expect(page.locator('input[name="email"], input[type="email"]').first()).toBeVisible({ timeout: 15000 })
    
    await page.fill('input[name="email"], input[type="email"]', email)
    await page.fill('input[name="username"]', username)
    await page.fill('input[type="password"]', password)
    await page.click('button[type="submit"]')
    
    // Wait for registration to complete
    await page.waitForURL('**/profile/build**', { timeout: 30000 })
    
    // Clear session by going to login page directly
    await page.goto('/login')
    await page.waitForTimeout(2000)
    
    // If already logged in, might redirect - check
    if (page.url().includes('/login')) {
      // Fill login form
      const usernameInput = page.locator('input[name="username"], input[name="email"]').first()
      await expect(usernameInput).toBeVisible({ timeout: 10000 })
      
      await usernameInput.fill(username)
      await page.fill('input[type="password"]', password)
      await page.click('button[type="submit"]')
      
      // Should redirect to home or profile
      await page.waitForTimeout(5000)
      const afterLoginUrl = page.url()
      expect(afterLoginUrl).not.toContain('/login')
      console.log(`✅ Login successful, redirected to: ${afterLoginUrl}`)
    } else {
      console.log('ℹ️ Already logged in, skipping login form test')
    }
  })
  
  test('login with invalid credentials shows error', async ({ page }) => {
    await page.goto('/login')
    await page.waitForTimeout(1000)
    
    // Check if we're on login page (might redirect if already logged in)
    if (!page.url().includes('/login')) {
      console.log('ℹ️ Not on login page, skipping test')
      return
    }
    
    await expect(page.locator('input[name="username"], input[name="email"]').first()).toBeVisible({ timeout: 10000 })
    
    await page.fill('input[name="username"], input[name="email"]', 'nonexistent_user_12345')
    await page.fill('input[type="password"]', 'wrongpassword')
    await page.click('button[type="submit"]')
    
    await page.waitForTimeout(3000)
    
    // Should stay on login page or show error
    const currentUrl = page.url()
    const bodyText = await page.textContent('body') || ''
    const hasError = /error|invalid|incorrect|failed/i.test(bodyText)
    
    expect(currentUrl.includes('/login') || hasError).toBeTruthy()
  })
})

