#!/usr/bin/env python3
"""
Minimal browser test with different approaches
"""
import asyncio
from playwright.async_api import async_playwright

async def test_different_browsers():
    print("🧪 Testing different browser configurations...")
    
    configurations = [
        {
            "name": "Chrome with minimal args",
            "browser_type": "chromium",
            "headless": False,
            "args": []
        },
        {
            "name": "Chrome headless (should work)",
            "browser_type": "chromium", 
            "headless": True,
            "args": []
        },
        {
            "name": "Firefox visible",
            "browser_type": "firefox",
            "headless": False,
            "args": []
        },
        {
            "name": "Chrome with safe args",
            "browser_type": "chromium",
            "headless": False,
            "args": ["--no-sandbox", "--disable-dev-shm-usage"]
        }
    ]
    
    for config in configurations:
        print(f"\n🔬 Testing: {config['name']}")
        
        playwright_instance = None
        browser = None
        page = None
        
        try:
            playwright_instance = await async_playwright().start()
            
            if config["browser_type"] == "chromium":
                browser = await playwright_instance.chromium.launch(
                    headless=config["headless"],
                    args=config["args"]
                )
            elif config["browser_type"] == "firefox":
                browser = await playwright_instance.firefox.launch(
                    headless=config["headless"],
                    args=config["args"]
                )
            
            page = await browser.new_page()
            await page.goto("https://www.google.com", timeout=5000)
            
            if not config["headless"]:
                print("⏰ Browser should be visible now for 3 seconds...")
                await page.wait_for_timeout(3000)
            
            print(f"✅ {config['name']} - SUCCESS!")
            
        except Exception as e:
            print(f"❌ {config['name']} - FAILED: {e}")
            
        finally:
            try:
                if page: await page.close()
                if browser: await browser.close()
                if playwright_instance: await playwright_instance.stop()
            except:
                pass
            
        await asyncio.sleep(1)  # Brief pause between tests

if __name__ == "__main__":
    asyncio.run(test_different_browsers())
