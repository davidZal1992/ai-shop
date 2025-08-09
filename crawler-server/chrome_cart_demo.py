#!/usr/bin/env python3
"""
Standalone Chrome demo for Shufersal cart - you WILL see the browser!
"""
import asyncio
from playwright.async_api import async_playwright

async def chrome_shufersal_demo():
    print("🎬 CHROME SHUFERSAL CART DEMO")
    print("=" * 50)
    print("🚀 This will open Chrome and show you the entire process!")
    print("📱 You'll see:")
    print("   1. Chrome browser opening")
    print("   2. Going to Shufersal")
    print("   3. Searching for milk")
    print("   4. Adding item to cart")
    print("   5. Showing the cart")
    print("⏰ Browser will stay open for 15 seconds at the end")
    print("=" * 50)
    
    playwright_instance = None
    browser = None
    page = None
    
    try:
        print("\n🚀 Starting Playwright...")
        playwright_instance = await async_playwright().start()
        
        print("🚀 Opening Chrome browser (VISIBLE)...")
        browser = await playwright_instance.chromium.launch(
            headless=False,
            slow_mo=2000,  # Very slow so you can see everything
            channel="chrome",  # Use your system Chrome
            args=['--no-sandbox', '--start-maximized']
        )
        
        print("📄 Creating new page...")
        page = await browser.new_page()
        
        print("🌐 Going to Shufersal...")
        await page.goto("https://www.shufersal.co.il/online/he/")
        await page.wait_for_timeout(3000)
        
        print("🔍 Searching for milk (חלב)...")
        search_input = await page.wait_for_selector('input[placeholder*="חיפוש"]', timeout=10000)
        await search_input.fill("חלב")
        await page.press('input[placeholder*="חיפוש"]', 'Enter')
        await page.wait_for_timeout(5000)
        
        print("📦 Looking for products...")
        products = await page.query_selector_all('li.SEARCH.tileBlock.miglog-prod')
        
        if products:
            print(f"✅ Found {len(products)} products!")
            
            # Try to add first product to cart
            first_product = products[0]
            product_name_element = await first_product.query_selector('[data-product-name]')
            
            if product_name_element:
                product_name = await product_name_element.get_attribute('data-product-name')
                print(f"🛒 Trying to add: {product_name}")
                
                # Click add to cart button
                add_button = await first_product.query_selector('button.js-add-to-cart')
                if add_button:
                    await add_button.click()
                    await page.wait_for_timeout(3000)
                    
                    # Check if it worked (look for update button)
                    update_button = await first_product.query_selector('button.js-update-cart')
                    if update_button:
                        print("🎉 SUCCESS! Item added to cart!")
                        
                        print("🛒 Navigating to cart page...")
                        await page.goto("https://www.shufersal.co.il/online/he/cart")
                        await page.wait_for_timeout(3000)
                        
                        print("✅ Cart page loaded!")
                    else:
                        print("⚠️ Add to cart clicked, but couldn't confirm success")
                else:
                    print("❌ Could not find add to cart button")
            else:
                print("❌ Could not get product name")
        else:
            print("❌ No products found")
        
        print("\n⏰ KEEPING BROWSER OPEN FOR 15 SECONDS...")
        print("👀 LOOK AT YOUR SCREEN - YOU SHOULD SEE CHROME!")
        await page.wait_for_timeout(15000)
        
        print("✅ Demo completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        
    finally:
        print("🧹 Closing browser...")
        try:
            if page: await page.close()
            if browser: await browser.close()
            if playwright_instance: await playwright_instance.stop()
        except:
            pass

if __name__ == "__main__":
    asyncio.run(chrome_shufersal_demo())
