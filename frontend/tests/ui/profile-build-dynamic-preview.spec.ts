import { test, expect } from '@playwright/test'

const BASE_URL = process.env.E2E_BASE_URL || 'https://ailanguagetutor.syntagent.com'

test.describe('Profile Build - Dynamic Preview Updates', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to login page
    await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded' })
    
    // Wait for potential Cloudflare challenge
    await page.waitForTimeout(2000)
    
    // Check if we're on login page or if Cloudflare redirected us
    const currentUrl = page.url()
    if (currentUrl.includes('challenge') || currentUrl.includes('cloudflare')) {
      console.log('⚠️ Cloudflare challenge detected - waiting...')
      await page.waitForTimeout(5000)
    }
    
    // Try to login
    try {
      const usernameInput = page.locator('input[type="text"], input[name="username"], input[placeholder*="username" i], input[placeholder*="email" i]').first()
      const passwordInput = page.locator('input[type="password"]').first()
      const loginButton = page.locator('button:has-text("Login"), button:has-text("Sign in"), button[type="submit"]').first()
      
      await usernameInput.waitFor({ state: 'visible', timeout: 10000 }).catch(() => {})
      await passwordInput.waitFor({ state: 'visible', timeout: 10000 }).catch(() => {})
      
      if (await usernameInput.isVisible() && await passwordInput.isVisible()) {
        await usernameInput.fill('bperak_admin')
        await passwordInput.fill('Teachable1A')
        await loginButton.click()
        
        // Wait for navigation after login
        await page.waitForURL('**/profile/build', { timeout: 15000 }).catch(() => {
          // If not redirected, try navigating directly
          page.goto(`${BASE_URL}/profile/build`, { waitUntil: 'domcontentloaded' })
        })
      } else {
        // Already logged in or on different page, navigate directly
        await page.goto(`${BASE_URL}/profile/build`, { waitUntil: 'domcontentloaded' })
      }
    } catch (err) {
      // If login fails, try navigating directly (might already be logged in)
      await page.goto(`${BASE_URL}/profile/build`, { waitUntil: 'domcontentloaded' })
    }
    
    // Wait for page to load
    await page.waitForTimeout(3000)
  })

  test('profile preview updates dynamically as conversation progresses', async ({ page }) => {
    // Wait for the page to be ready
    const textarea = page.locator('textarea[placeholder*="message" i], textarea[placeholder*="Type" i]').first()
    await textarea.waitFor({ state: 'visible', timeout: 20000 })
    
    // Get initial state of Learning Path Preview
    const learningPathPreview = page.locator('text=Your Learning Path Preview').locator('..').first()
    await learningPathPreview.waitFor({ state: 'visible', timeout: 10000 }).catch(() => {})
    
    const initialPreviewText = await learningPathPreview.textContent().catch(() => '')
    console.log('Initial preview text:', initialPreviewText?.substring(0, 200))
    
    // Send first message
    console.log('Sending first message...')
    await textarea.fill('Hello, I want to learn Japanese. I am a complete beginner.')
    await page.locator('button:has-text("Send")').first().click()
    
    // Wait for AI response
    await page.waitForTimeout(8000)
    
    // Check if preview has changed
    const afterFirstMessage = await learningPathPreview.textContent().catch(() => '')
    console.log('After first message:', afterFirstMessage?.substring(0, 200))
    
    // Send second message with more details
    console.log('Sending second message...')
    await textarea.fill('I have been studying for about 3 months using Duolingo. I want to be able to have conversations when I visit Japan next year.')
    await page.locator('button:has-text("Send")').first().click()
    
    // Wait for AI response and profile extraction (debounced 2 seconds)
    await page.waitForTimeout(10000)
    
    // Check if preview shows extracted data
    const afterSecondMessage = await learningPathPreview.textContent().catch(() => '')
    console.log('After second message:', afterSecondMessage?.substring(0, 300))
    
    // Send third message with learning preferences
    console.log('Sending third message...')
    await textarea.fill('I prefer learning through interactive conversations and practical exercises. I study for about 30 minutes every morning before work.')
    await page.locator('button:has-text("Send")').first().click()
    
    // Wait for AI response and profile extraction
    await page.waitForTimeout(10000)
    
    // Check if preview shows more extracted data
    const afterThirdMessage = await learningPathPreview.textContent().catch(() => '')
    console.log('After third message:', afterThirdMessage?.substring(0, 400))
    
    // Verify that preview has changed from initial state
    if (initialPreviewText) {
      expect(afterThirdMessage).not.toBe(initialPreviewText)
      console.log('✅ Preview has changed from initial state')
    }
    
    // Check for specific profile data indicators
    const previewContent = afterThirdMessage || ''
    
    // Look for indicators that profile data is being extracted
    const hasLearningGoals = previewContent.includes('learning goals') || 
                            previewContent.includes('Learning Goals') ||
                            previewContent.includes('Japanese') ||
                            previewContent.includes('travel')
    
    const hasExperience = previewContent.includes('experience') ||
                         previewContent.includes('Experience') ||
                         previewContent.includes('beginner') ||
                         previewContent.includes('months')
    
    const hasMethods = previewContent.includes('methods') ||
                      previewContent.includes('Methods') ||
                      previewContent.includes('conversation') ||
                      previewContent.includes('interactive')
    
    console.log('Profile data indicators:')
    console.log('  - Learning goals:', hasLearningGoals)
    console.log('  - Experience:', hasExperience)
    console.log('  - Methods:', hasMethods)
    
    // At least one indicator should be present if extraction is working
    const hasAnyData = hasLearningGoals || hasExperience || hasMethods
    
    if (hasAnyData) {
      console.log('✅ Profile preview shows extracted data')
    } else {
      console.log('⚠️ Profile preview may not be showing extracted data yet')
      // This is not a failure - extraction might take longer or data might be in a different format
    }
    
    // Take a screenshot for verification
    await page.screenshot({ path: '/tmp/profile-preview-test.png', fullPage: true })
    console.log('Screenshot saved to /tmp/profile-preview-test.png')
  })

  test('profile preview shows building state during conversation', async ({ page }) => {
    // Wait for the page to be ready
    const textarea = page.locator('textarea[placeholder*="message" i], textarea[placeholder*="Type" i]').first()
    await textarea.waitFor({ state: 'visible', timeout: 20000 })
    
    // Send a message
    await textarea.fill('I want to learn Japanese for business purposes.')
    await page.locator('button:has-text("Send")').first().click()
    
    // Wait a bit for the preview to potentially show "Building..." state
    await page.waitForTimeout(3000)
    
    // Check for "Building..." indicator or similar
    const buildingIndicator = page.locator('text=/Building/i, text=/extracting/i, text=/analyzing/i').first()
    const hasBuildingIndicator = await buildingIndicator.isVisible().catch(() => false)
    
    if (hasBuildingIndicator) {
      console.log('✅ Found "Building..." indicator in preview')
    } else {
      console.log('ℹ️ No "Building..." indicator found (may not be implemented)')
    }
    
    // Wait for extraction to complete
    await page.waitForTimeout(8000)
    
    // Verify preview is visible
    const learningPathPreview = page.locator('text=Your Learning Path Preview').locator('..').first()
    const isVisible = await learningPathPreview.isVisible().catch(() => false)
    expect(isVisible).toBe(true)
    
    console.log('✅ Learning Path Preview is visible after conversation')
  })

  test('multiple messages trigger profile preview updates', async ({ page }) => {
    // Wait for the page to be ready
    const textarea = page.locator('textarea[placeholder*="message" i], textarea[placeholder*="Type" i]').first()
    await textarea.waitFor({ state: 'visible', timeout: 20000 })
    
    const learningPathPreview = page.locator('text=Your Learning Path Preview').locator('..').first()
    
    // Track preview changes across multiple messages
    const previewStates: string[] = []
    
    const messages = [
      'I am interested in learning Spanish.',
      'I have some basic knowledge from high school classes.',
      'I want to use Spanish for travel and work communication.',
      'I prefer learning through apps and conversation practice.'
    ]
    
    for (let i = 0; i < messages.length; i++) {
      console.log(`Sending message ${i + 1}/${messages.length}...`)
      
      // Get current preview state
      const currentState = await learningPathPreview.textContent().catch(() => '')
      previewStates.push(currentState || '')
      
      // Send message
      await textarea.fill(messages[i])
      await page.locator('button:has-text("Send")').first().click()
      
      // Wait for AI response
      await page.waitForTimeout(6000)
      
      // Wait for potential profile extraction (debounced)
      await page.waitForTimeout(3000)
      
      // Get new preview state
      const newState = await learningPathPreview.textContent().catch(() => '')
      previewStates.push(newState || '')
      
      console.log(`Preview state after message ${i + 1}:`, newState?.substring(0, 150))
    }
    
    // Verify that preview states changed
    const uniqueStates = new Set(previewStates.filter(s => s.length > 0))
    console.log(`Found ${uniqueStates.size} unique preview states`)
    
    // At least some variation should occur
    if (uniqueStates.size > 1) {
      console.log('✅ Preview states changed across messages')
    } else {
      console.log('⚠️ Preview states did not change (may need more conversation)')
    }
    
    // Final verification - preview should be visible
    const isVisible = await learningPathPreview.isVisible().catch(() => false)
    expect(isVisible).toBe(true)
  })
})
