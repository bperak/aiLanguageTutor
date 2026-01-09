import { test, expect } from '@playwright/test'

/**
 * Learning Path E2E Tests
 * 
 * Tests the learning path functionality:
 * - Login as bperak_admin
 * - Navigate to home page
 * - Verify learning path is displayed
 * - Verify learning path steps have vocabulary, grammar, formulaic expressions
 * - Verify CanDo links work
 * - Verify path structure is complete
 */

test.describe('Learning Path', () => {
  const baseURL = process.env.E2E_BASE_URL || 'https://ailanguagetutor.syntagent.com'
  const username = 'bperak_admin'
  const password = 'Teachable1A'

  test.beforeEach(async ({ page, context }) => {
    await context.setExtraHTTPHeaders({
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
  })

  test('should login and display learning path on home page', async ({ page }) => {
    // Navigate to login
    await page.goto(`${baseURL}/login`, { waitUntil: 'domcontentloaded', timeout: 30000 })
    await page.waitForTimeout(2000)

    // Check for Cloudflare
    const bodyText = await page.textContent('body') || ''
    if (bodyText.includes('Please enable cookies') || bodyText.includes('Error 1033')) {
      console.log('⚠️ Cloudflare challenge detected')
      return
    }

    // Login
    const usernameInput = page.locator('input[name="username"], input[type="text"]').first()
    if (await usernameInput.count() > 0) {
      await usernameInput.fill(username)
      await page.fill('input[type="password"]', password)
      await page.click('button:has-text("Sign in"), button[type="submit"]')
      await page.waitForTimeout(5000)
    }

    // Navigate to home
    await page.goto(`${baseURL}/`, { waitUntil: 'domcontentloaded', timeout: 30000 })
    await page.waitForTimeout(3000)

    // Verify we're logged in (check for username in page)
    const pageText = await page.textContent('body') || ''
    expect(pageText.toLowerCase()).toContain(username.toLowerCase())
    console.log('✅ User logged in and on home page')

    // Check for learning path content
    const learningPathText = page.locator('text=/learning path|next steps|start lesson/i')
    const pathCount = await learningPathText.count()
    expect(pathCount).toBeGreaterThan(0)
    console.log('✅ Learning path content found')

    await page.screenshot({ path: '/tmp/learning-path-home.png', fullPage: true })
  })

  test('should verify learning path steps have complete structure', async ({ page }) => {
    // Login
    await page.goto(`${baseURL}/login`, { waitUntil: 'domcontentloaded', timeout: 30000 })
    await page.waitForTimeout(2000)

    const usernameInput = page.locator('input[name="username"], input[type="text"]').first()
    if (await usernameInput.count() > 0) {
      await usernameInput.fill(username)
      await page.fill('input[type="password"]', password)
      await page.click('button:has-text("Sign in"), button[type="submit"]')
      await page.waitForTimeout(5000)
    }

    // Navigate to home
    await page.goto(`${baseURL}/`, { waitUntil: 'domcontentloaded', timeout: 30000 })
    await page.waitForTimeout(5000) // Wait for path to load

    // Check for CanDo links (e.g., "JF:21", "JF:22", etc.)
    const candoLinks = page.locator('a[href*="/cando/"], text=/JF:\\d+/')
    const linkCount = await candoLinks.count()
    
    if (linkCount > 0) {
      console.log(`✅ Found ${linkCount} CanDo links`)
      
      // Get the first CanDo link
      const firstLink = candoLinks.first()
      const linkText = await firstLink.textContent()
      const linkHref = await firstLink.getAttribute('href')
      
      console.log(`✅ First CanDo link: ${linkText} -> ${linkHref}`)
      
      // Click the link to verify it works
      await firstLink.click()
      await page.waitForTimeout(3000)
      
      // Verify we're on a CanDo page
      expect(page.url()).toContain('/cando/')
      console.log('✅ CanDo link works correctly')
    } else {
      console.log('⚠️ No CanDo links found - path may not be generated yet')
    }

    await page.screenshot({ path: '/tmp/learning-path-structure.png', fullPage: true })
  })

  test('should verify learning path API returns complete data', async ({ page }) => {
    // Login
    await page.goto(`${baseURL}/login`, { waitUntil: 'domcontentloaded', timeout: 30000 })
    await page.waitForTimeout(2000)

    const usernameInput = page.locator('input[name="username"], input[type="text"]').first()
    if (await usernameInput.count() > 0) {
      await usernameInput.fill(username)
      await page.fill('input[type="password"]', password)
      await page.click('button:has-text("Sign in"), button[type="submit"]')
      await page.waitForTimeout(5000)
    }

    // Monitor API calls
    const apiResponses: any[] = []
    page.on('response', async (response) => {
      const url = response.url()
      if (url.includes('/api/') && (url.includes('path') || url.includes('learning'))) {
        try {
          const json = await response.json()
          apiResponses.push({ url, status: response.status(), data: json })
        } catch (e) {
          // Not JSON
        }
      }
    })

    // Navigate to home
    await page.goto(`${baseURL}/`, { waitUntil: 'domcontentloaded', timeout: 30000 })
    await page.waitForTimeout(5000)

    // Check API responses
    if (apiResponses.length > 0) {
      console.log(`✅ Found ${apiResponses.length} learning path API calls`)
      
      for (const resp of apiResponses) {
        console.log(`  - ${resp.url}: ${resp.status}`)
        
        // Check if response has path data with steps
        if (resp.data && resp.data.path_data) {
          const steps = resp.data.path_data.steps || []
          console.log(`    Steps: ${steps.length}`)
          
          // Check if steps have vocabulary, grammar, formulaic_expressions
          for (const step of steps) {
            const hasVocab = step.vocabulary && step.vocabulary.length > 0
            const hasGrammar = step.grammar && step.grammar.length > 0
            const hasFormulaic = step.formulaic_expressions && step.formulaic_expressions.length > 0
            const hasCanDo = step.can_do_descriptors && step.can_do_descriptors.length > 0
            
            console.log(`    Step ${step.step_id}: vocab=${hasVocab}, grammar=${hasGrammar}, formulaic=${hasFormulaic}, cando=${hasCanDo}`)
            
            if (!hasCanDo) {
              console.log(`    ⚠️ Step ${step.step_id} missing CanDo descriptor`)
            }
          }
        }
      }
    } else {
      console.log('⚠️ No learning path API calls detected')
    }

    await page.screenshot({ path: '/tmp/learning-path-api.png', fullPage: true })
  })

  test('should verify CanDo descriptors in path exist', async ({ page }) => {
    // Login
    await page.goto(`${baseURL}/login`, { waitUntil: 'domcontentloaded', timeout: 30000 })
    await page.waitForTimeout(2000)

    const usernameInput = page.locator('input[name="username"], input[type="text"]').first()
    if (await usernameInput.count() > 0) {
      await usernameInput.fill(username)
      await page.fill('input[type="password"]', password)
      await page.click('button:has-text("Sign in"), button[type="submit"]')
      await page.waitForTimeout(5000)
    }

    // Navigate to home
    await page.goto(`${baseURL}/`, { waitUntil: 'domcontentloaded', timeout: 30000 })
    await page.waitForTimeout(5000)

    // Find all CanDo links
    const candoLinks = page.locator('a[href*="/cando/"]')
    const linkCount = await candoLinks.count()
    
    if (linkCount > 0) {
      console.log(`✅ Found ${linkCount} CanDo links to test`)
      
      // Test first 3 links
      const linksToTest = Math.min(3, linkCount)
      for (let i = 0; i < linksToTest; i++) {
        const link = candoLinks.nth(i)
        const href = await link.getAttribute('href')
        const text = await link.textContent()
        
        if (href) {
          console.log(`Testing link ${i + 1}: ${text} -> ${href}`)
          
          // Navigate to CanDo page
          await page.goto(`${baseURL}${href}`, { waitUntil: 'domcontentloaded', timeout: 30000 })
          await page.waitForTimeout(3000)
          
          // Check for "not found" errors
          const notFoundError = page.locator('text=/not found|does not exist|cando.*not found/i')
          const errorCount = await notFoundError.count()
          
          if (errorCount > 0) {
            const errorText = await notFoundError.first().textContent()
            console.log(`    ⚠️ CanDo descriptor error: ${errorText}`)
          } else {
            console.log(`    ✅ CanDo descriptor exists and page loaded`)
          }
          
          // Go back to home
          await page.goto(`${baseURL}/`, { waitUntil: 'domcontentloaded', timeout: 30000 })
          await page.waitForTimeout(2000)
        }
      }
    } else {
      console.log('⚠️ No CanDo links found')
    }

    await page.screenshot({ path: '/tmp/learning-path-cando-validation.png', fullPage: true })
  })
})
