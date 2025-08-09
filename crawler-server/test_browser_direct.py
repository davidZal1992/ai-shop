#!/usr/bin/env python3
"""
Direct test of browser visibility without server
"""
import asyncio
from playwright.async_api import async_playwright

async def test_browser_visibility():
    print("🧪 Testing browser visibility directly...")
    
    playwright_instance = None
    browser = None
    page = None
    
    try:
        print("🚀 Starting Playwright...")
        playwright_instance = await async_playwright().start()
        
        print("🚀 Launching browser with headless=False...")
        browser = await playwright_instance.chromium.launch(
            headless=False,
            slow_mo=1000,
            args=[
                '--no-sandbox',
                '--start-maximized',
                '--new-window'
            ]
        )
        
        print("📄 Creating new page...")
        page = await browser.new_page()
        
        print("🌐 Navigating to Google...")
        await page.goto("https://www.google.com")
        
        print("⏰ Waiting 10 seconds - YOU SHOULD SEE A CHROME WINDOW NOW!")
        await page.wait_for_timeout(10000)
        
        print("✅ Test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
        
    finally:
        print("🧹 Cleaning up...")
        try:
            if page:
                await page.close()
            if browser:
                await browser.close()
            if playwright_instance:
                await playwright_instance.stop()
        except Exception as cleanup_error:
            print(f"⚠️ Cleanup error: {cleanup_error}")

if __name__ == "__main__":
    result = asyncio.run(test_browser_visibility())
    if result:
        print("🎉 Browser visibility test PASSED!")
    else:
        print("❌ Browser visibility test FAILED!")
