#!/usr/bin/env python3
"""
Test different Chrome configurations to fix visibility issues
"""
import asyncio
from playwright.async_api import async_playwright

async def test_chrome_configurations():
    print("🔧 Testing Chrome configurations for macOS visibility...")
    
    configurations = [
        {
            "name": "Chrome with macOS specific args",
            "headless": False,
            "args": [
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-software-rasterizer',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--disable-features=TranslateUI',
                '--disable-ipc-flooding-protection'
            ]
        },
        {
            "name": "Chrome with minimal safe args",
            "headless": False,
            "args": [
                '--no-sandbox',
                '--disable-dev-shm-usage'
            ]
        },
        {
            "name": "Chrome with user data dir",
            "headless": False,
            "args": [
                '--no-sandbox',
                '--user-data-dir=/tmp/playwright-chrome'
            ]
        },
        {
            "name": "Chrome with channel stable",
            "headless": False,
            "channel": "chrome",
            "args": ['--no-sandbox']
        }
    ]
    
    for i, config in enumerate(configurations, 1):
        print(f"\n🔬 Test {i}: {config['name']}")
        
        playwright_instance = None
        browser = None
        page = None
        
        try:
            playwright_instance = await async_playwright().start()
            
            launch_args = {
                "headless": config["headless"],
                "args": config["args"]
            }
            
            # Add channel if specified
            if "channel" in config:
                launch_args["channel"] = config["channel"]
            
            browser = await playwright_instance.chromium.launch(**launch_args)
            page = await browser.new_page()
            
            print("🌐 Navigating to Google...")
            await page.goto("https://www.google.com", timeout=10000)
            
            print("⏰ SUCCESS! Browser should be visible for 5 seconds...")
            await page.wait_for_timeout(5000)
            
            print(f"✅ {config['name']} - WORKS!")
            return config  # Return the working configuration
            
        except Exception as e:
            print(f"❌ {config['name']} - FAILED: {str(e)[:100]}...")
            
        finally:
            try:
                if page: await page.close()
                if browser: await browser.close()
                if playwright_instance: await playwright_instance.stop()
            except:
                pass
            
        await asyncio.sleep(1)
    
    print("\n❌ All Chrome configurations failed!")
    return None

if __name__ == "__main__":
    working_config = asyncio.run(test_chrome_configurations())
    if working_config:
        print(f"\n🎉 WORKING CONFIGURATION FOUND:")
        print(f"   Name: {working_config['name']}")
        print(f"   Args: {working_config['args']}")
    else:
        print("\n💡 RECOMMENDATION: Use Firefox for visible browsing, Chrome for headless.")
