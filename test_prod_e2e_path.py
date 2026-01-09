#!/usr/bin/env python3
"""
E2E test for production site: Register, complete profile, verify learning path
"""

import asyncio
import json
import time
from pathlib import Path
from playwright.async_api import async_playwright

PRODUCTION_URL = "https://ailanguagetutor.syntagent.com"
DEBUG_LOG_PATH = Path("/home/benedikt/.cursor/debug.log")


def log_debug(session_id: str, run_id: str, hypothesis_id: str, location: str, message: str, data: dict):
    """Write debug log entry."""
    try:
        DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(DEBUG_LOG_PATH, "a") as f:
            f.write(json.dumps({
                "sessionId": session_id,
                "runId": run_id,
                "hypothesisId": hypothesis_id,
                "location": location,
                "message": message,
                "data": data,
                "timestamp": int(time.time() * 1000)
            }) + "\n")
    except Exception:
        pass


async def test_production_e2e():
    """Run E2E test on production site."""
    run_id = f"prod-e2e-{int(time.time())}"
    session_id = "debug-session"
    
    print("=" * 80)
    print("PRODUCTION E2E TEST: Register -> Profile -> Learning Path")
    print(f"Testing: {PRODUCTION_URL}")
    print("=" * 80)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Step 1: Navigate to home page
            print("\n[1] Navigating to home page...")
            log_debug(session_id, run_id, "E2E1", "test_prod_e2e_path.py", "Navigate to home", {})
            start = time.time()
            await page.goto(PRODUCTION_URL, wait_until="domcontentloaded", timeout=30000)
            duration = (time.time() - start) * 1000
            log_debug(session_id, run_id, "E2E1", "test_prod_e2e_path.py", "Home page loaded", {"duration_ms": duration})
            print(f"   Loaded in {duration:.2f}ms")
            
            # Step 2: Click register link
            print("\n[2] Clicking register link...")
            register_link = await page.locator('a[href="/register"], a:has-text("Get started")').first
            if await register_link.count() > 0:
                await register_link.click()
                await page.wait_for_timeout(2000)
                print("   Clicked register link")
            else:
                print("   ⚠️  Register link not found, trying direct navigation")
                await page.goto(f"{PRODUCTION_URL}/register", wait_until="domcontentloaded")
            
            # Step 3: Fill registration form
            print("\n[3] Filling registration form...")
            timestamp = int(time.time() * 1000)
            username = f"e2etest_{timestamp}"
            email = f"e2etest_{timestamp}@example.com"
            password = "TestPass123"
            
            await page.fill('input[type="email"], input[name="email"]', email)
            await page.fill('input[name="username"]', username)
            await page.fill('input[type="password"]', password)
            await page.wait_for_timeout(1000)
            print(f"   Filled form: {username}")
            
            # Step 4: Submit registration
            print("\n[4] Submitting registration...")
            submit_start = time.time()
            submit_button = page.locator('button[type="submit"]')
            await submit_button.click()
            log_debug(session_id, run_id, "E2E2", "test_prod_e2e_path.py", "Registration submitted", {"timestamp": timestamp})
            
            # Wait for redirect
            await page.wait_for_url("**/profile/build**", timeout=15000)
            submit_duration = (time.time() - submit_start) * 1000
            print(f"   Registration completed in {submit_duration:.2f}ms")
            print(f"   Redirected to: {page.url}")
            
            # Step 5: Start profile building session
            print("\n[5] Starting profile building session...")
            await page.wait_for_timeout(2000)
            
            # Look for start/begin button or chat interface
            start_button = page.locator('button:has-text("Start"), button:has-text("Begin"), button:has-text("Create")')
            if await start_button.count() > 0:
                await start_button.first.click()
                await page.wait_for_timeout(2000)
                print("   Started session")
            
            # Step 6: Send profile messages
            print("\n[6] Sending profile messages...")
            textarea = page.locator('textarea, input[type="text"]')
            send_button = page.locator('button:has-text("Send"), button[type="submit"]')
            
            if await textarea.count() > 0:
                await textarea.fill("I want to learn Japanese for travel. I have no prior experience.")
                await page.wait_for_timeout(500)
                if await send_button.count() > 0:
                    await send_button.first.click()
                    await page.wait_for_timeout(3000)
                    print("   Sent first message")
                
                await textarea.fill("I prefer interactive learning with conversations. I can study 30 minutes per day.")
                await page.wait_for_timeout(500)
                if await send_button.count() > 0:
                    await send_button.first.click()
                    await page.wait_for_timeout(3000)
                    print("   Sent second message")
            
            # Step 7: Complete profile
            print("\n[7] Completing profile...")
            complete_button = page.locator('button:has-text("Complete"), button:has-text("Finish"), button:has-text("Done")')
            if await complete_button.count() > 0:
                await complete_button.first.click()
                await page.wait_for_timeout(2000)
                print("   Clicked complete button")
            
            # Wait for redirect to home
            try:
                await page.wait_for_url("**/", timeout=10000)
            except:
                pass
            
            # Step 8: Check for learning path
            print("\n[8] Checking for learning path...")
            await page.wait_for_timeout(5000)
            
            # Check multiple times (polling)
            path_found = False
            for i in range(6):  # Check 6 times over 30 seconds
                await page.wait_for_timeout(5000)
                body_text = await page.inner_text('body')
                has_path = 'next step' in body_text.lower() or 'learning path' in body_text.lower() or 'your path' in body_text.lower()
                has_building = 'building in background' in body_text.lower() or 'generating' in body_text.lower()
                
                log_debug(session_id, run_id, "E2E3", "test_prod_e2e_path.py", f"Path check {i+1}", {
                    "has_path": has_path,
                    "has_building": has_building,
                    "url": page.url
                })
                
                if has_path and not has_building:
                    path_found = True
                    print(f"   ✅ Learning path found! (check {i+1})")
                    break
                elif has_building:
                    print(f"   ⏳ Path still generating... (check {i+1})")
                else:
                    print(f"   ⏳ Waiting for path... (check {i+1})")
            
            # Step 9: Take screenshot
            print("\n[9] Taking screenshot...")
            screenshot_path = "/tmp/production_e2e_path_screenshot.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"   Screenshot saved: {screenshot_path}")
            
            # Final check
            body_text = await page.inner_text('body')
            final_check = {
                "url": page.url,
                "has_path": 'next step' in body_text.lower() or 'learning path' in body_text.lower(),
                "has_building": 'building in background' in body_text.lower(),
                "path_visible": 'next step' in body_text.lower() and 'building' not in body_text.lower(),
                "text_preview": body_text[:300]
            }
            
            log_debug(session_id, run_id, "E2E4", "test_prod_e2e_path.py", "E2E test completed", final_check)
            
            # Summary
            print("\n" + "=" * 80)
            print("E2E TEST SUMMARY")
            print("=" * 80)
            print(f"URL: {final_check['url']}")
            print(f"Learning Path Found: {final_check['has_path']}")
            print(f"Path Visible (not building): {final_check['path_visible']}")
            if final_check['path_visible']:
                print("✅ SUCCESS: Learning path is visible!")
            else:
                print("⚠️  Learning path not yet visible or still building")
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            # Take error screenshot
            try:
                await page.screenshot(path="/tmp/production_e2e_path_error.png", full_page=True)
                print("Error screenshot saved: /tmp/production_e2e_path_error.png")
            except:
                pass
        finally:
            await browser.close()


if __name__ == "__main__":
    if DEBUG_LOG_PATH.exists():
        DEBUG_LOG_PATH.unlink()
        print(f"Cleared debug log: {DEBUG_LOG_PATH}")
    
    try:
        asyncio.run(test_production_e2e())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\nTest failed: {e}")
        import traceback
        traceback.print_exc()

