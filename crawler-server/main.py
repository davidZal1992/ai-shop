"""
Shufersal Search Crawler Server - FastAPI server for searching Shufersal products
"""
from fastapi import FastAPI, HTTPException
from numpy import double
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import asyncio
import urllib.parse
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import time
import json
import re
from loguru import logger
import sys

# Configure loguru for better visibility
logger.remove()  # Remove default handler
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="DEBUG",
    colorize=True
)
logger.add(
    "crawler_server.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
    rotation="10 MB",
    retention="7 days"
)

app = FastAPI(
    title="Shufersal Search Crawler",
    description="Search and parse products from Shufersal website",
    version="2.0.0"
)

# Request/Response Models
class SearchRequest(BaseModel):
    search_term: str
    wait_time: Optional[int] = 5
    take_screenshot: Optional[bool] = False
    load_all_pages: Optional[bool] = True
    max_scrolls: Optional[int] = 5

class CartItem(BaseModel):
    product_code: str
    quantity: float
    product_name: str = ""  # For logging
    search_url: Optional[str] = None  # URL of the search results page

class AddToCartRequest(BaseModel):
    # Support both single item and array of items
    items: List[CartItem] = []  # Array of items
    
class CartItemResult(BaseModel):
    success: bool
    product_code: str
    quantity: float
    product_name: str
    message: str
    error: Optional[str] = None

class AddToCartResponse(BaseModel):
    success: bool
    total_items: int
    successful_items: int
    failed_items: int
    results: List[CartItemResult]
    message: str
    error: Optional[str] = None

class ProductInfo(BaseModel):
    name: str
    price: float
    product_code: str
    brand: Optional[str] = None
    size: Optional[str] = None
    unit: Optional[str] = None
    price_per_unit: Optional[str] = None
    promotion: Optional[str] = None
    in_stock: bool = True
    product_url: Optional[str] = None
    image_url: Optional[str] = None

class SearchResponse(BaseModel):
    success: bool
    search_term: str
    products: List[ProductInfo]
    total_found: int
    search_url: str
    screenshot_path: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}

# Global browser instance (for performance)
browser = None
playwright_instance = None

async def get_browser():
    """Get or create browser instance with robust error handling"""
    global browser, playwright_instance
    
    # Check if browser needs to be created or recreated
    needs_new_browser = False
    
    if browser is None:
        needs_new_browser = True
        logger.info("🔄 Browser is None, creating new browser")
    else:
        # Test if browser is still working
        try:
            # Try multiple tests to ensure browser is alive
            contexts = browser.contexts
            is_connected = browser.is_connected()
            
            if not is_connected:
                logger.warning("⚠️ Browser is not connected, recreating")
                needs_new_browser = True
                browser = None
            else:
                logger.debug("✅ Browser is alive and connected")
                
        except Exception as e:
            # Browser is closed or invalid
            logger.warning(f"⚠️ Browser test failed: {e}, recreating browser")
            needs_new_browser = True
            browser = None
    
    if needs_new_browser:
        # Clean up old instances first
        await cleanup_browser_instances()
        
        try:
            # Create new instances
            logger.info("🚀 Creating new Playwright instance...")
            playwright_instance = await async_playwright().start()
            
            logger.info("🚀 Launching new headless browser...")
            browser = await playwright_instance.chromium.launch(
                headless=True,  # Back to headless for stability and performance
                args=[
                    '--no-sandbox', 
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--no-first-run',
                    '--disable-background-timer-throttling'
                ]
            )
            logger.info("🌐 Headless browser launched successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to create browser: {e}")
            await cleanup_browser_instances()
            raise
    
    return browser

async def cleanup_browser_instances():
    """Clean up global browser instances"""
    global browser, playwright_instance
    
    # Clean up browser
    if browser:
        try:
            await browser.close()
            logger.debug("🔒 Old browser closed")
        except Exception as e:
            logger.debug(f"⚠️ Error closing browser: {e}")
    
    # Clean up playwright
    if playwright_instance:
        try:
            await playwright_instance.stop()
            logger.debug("🔒 Old Playwright stopped")
        except Exception as e:
            logger.debug(f"⚠️ Error stopping Playwright: {e}")
    
    # Reset globals
    browser = None
    playwright_instance = None

def parse_shufersal_products(html_content: str, base_url: str = "https://www.shufersal.co.il") -> List[ProductInfo]:
    """
    Parse Shufersal product HTML and extract structured product information
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    products = []
    
    # Find all product items with the specific structure
    product_items = soup.find_all('li', class_=lambda x: x and 'SEARCH' in x and 'tileBlock' in x)
    
    logger.info(f"🔍 Found {len(product_items)} product items to parse")
    
    for item in product_items:
        try:
            # Extract basic product data from attributes
            product_name = item.get('data-product-name', '').strip()
            product_price = item.get('data-product-price', '0')
            product_code = item.get('data-product-code', '').strip()
            
            if not product_name or not product_code:
                continue
                
            # Convert price to float
            try:
                price = float(product_price)
            except (ValueError, TypeError):
                price = 0.0
            
            # Extract additional details from the HTML content
            brand = None
            size = None
            unit = None
            price_per_unit = None
            promotion = None
            product_url = None
            
            # Extract brand and size from smallText div
            small_text_div = item.find('div', class_='smallText')
            if small_text_div:
                text_content = small_text_div.get_text(strip=True)
                # Split by | to get size and brand
                parts = [part.strip() for part in text_content.split('|')]
                if len(parts) >= 1:
                    size = parts[0]
                if len(parts) >= 2:
                    brand = parts[1]
            
            # Extract unit from unitPick span
            unit_pick = item.find('span', class_='unitPick')
            if unit_pick:
                unit_text = unit_pick.get_text(strip=True)
                unit = unit_text
            
            # Extract price per unit
            price_per_unit_div = item.find('div', class_='pricePerUnit')
            if price_per_unit_div:
                price_per_unit = price_per_unit_div.get_text(strip=True)
                # Clean up extra spaces and newlines
                price_per_unit = re.sub(r'\s+', ' ', price_per_unit)
            
            # Check for promotions
            promotion_div = item.find('div', class_='promotion-section')
            if promotion_div:
                promotion_text = promotion_div.find('strong')
                if promotion_text:
                    promotion = promotion_text.get_text(strip=True)
                    # Clean up promotion text
                    promotion = re.sub(r'\s+', ' ', promotion)
            
            
            # Skip product URL - not necessary
            product_url = None
            
            # Create product info object
            product = ProductInfo(
                name=product_name,
                price=price,
                product_code=product_code,
                brand=brand,
                size=size,
                unit=unit,
                price_per_unit=price_per_unit,
                promotion=promotion,
                product_url=product_url,
            )
            
            products.append(product)
            logger.debug(f"✅ Parsed product: {product_name} - ₪{price}")
            
        except Exception as e:
            logger.warning(f"⚠️ Error parsing product item: {e}")
            continue
    
    logger.info(f"✅ Successfully parsed {len(products)} products")
    return products

async def load_all_products_with_scroll(page, max_scrolls: int = 4):
    """
    Handle infinite scroll to load all products on Shufersal search results page with robust error handling
    """
    logger.info(f"🔄 Starting infinite scroll (max {max_scrolls} scrolls)")
    
    previous_product_count = 0
    scroll_count = 0
    no_change_count = 0
    
    while scroll_count < max_scrolls:
        try:
            # Count current products with error handling
            try:
                current_products = await page.query_selector_all('li.SEARCH.tileBlock')
                current_count = len(current_products)
            except Exception as e:
                logger.warning(f"⚠️ Failed to count products on scroll {scroll_count + 1}: {e}")
                break  # Exit if we can't count products
            
            logger.info(f"📊 Scroll {scroll_count + 1}: Found {current_count} products")
            
            # If no new products loaded after scrolling, try a few more times then stop
            if current_count == previous_product_count:
                no_change_count += 1
                if no_change_count >= 3:
                    logger.info("🛑 No more products loading, stopping scroll")
                    break
            else:
                no_change_count = 0
            
            previous_product_count = current_count
            
            # Scroll to bottom of page with error handling
            try:
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                logger.debug(f"✅ Scrolled to bottom (scroll {scroll_count + 1})")
            except Exception as e:
                logger.warning(f"⚠️ Failed to scroll on attempt {scroll_count + 1}: {e}")
                break  # Exit if we can't scroll
            
            # Wait for new content to load (shorter timeout)
            try:
                await page.wait_for_timeout(1500)  # Reduced from 2000ms
            except Exception as e:
                logger.warning(f"⚠️ Wait timeout failed: {e}")
                break
            
            # Try to wait for new products to appear (with shorter timeout and error handling)
            try:
                await page.wait_for_function(
                    f"document.querySelectorAll('li.SEARCH.tileBlock').length > {current_count}",
                    timeout=3000  # Reduced from 5000ms
                )
                logger.debug(f"✅ New products loaded after scroll {scroll_count + 1}")
            except Exception as e:
                # This is expected when no more products load
                logger.debug(f"⏳ No new products after scroll {scroll_count + 1} (timeout/error: {e})")
            
            scroll_count += 1
            
        except Exception as e:
            logger.error(f"❌ Critical error during scroll {scroll_count + 1}: {e}")
            break  # Exit on any critical error
    
    # Final count with error handling
    try:
        final_products = await page.query_selector_all('li.SEARCH.tileBlock')
        final_count = len(final_products)
    except Exception as e:
        logger.warning(f"⚠️ Failed to get final product count: {e}")
        final_count = previous_product_count  # Use last known count
    
    logger.info(f"✅ Infinite scroll completed: {final_count} total products loaded after {scroll_count} scrolls")

@app.on_event("startup")
async def startup_event():
    """Initialize browser on startup"""
    logger.info("🔄 Starting up Shufersal Search Crawler...")
    logger.info("📝 Logging is configured and working!")
    logger.debug("🐛 Debug logging is enabled")
    await get_browser()
    logger.info("🚀 Shufersal Search Crawler started successfully!")
    logger.info("📍 Server running at: http://localhost:8000")
    logger.info("📖 API docs available at: http://localhost:8000/docs")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up browser on shutdown"""
    logger.info("🔄 Shutting down crawler server...")
    await cleanup_browser_instances()
    logger.info("✅ Shutdown complete")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Shufersal Search Crawler is running",
        "version": "2.0.0",
        "endpoints": [
            "/search - Search for products (headless)",
            "/add-to-cart - Add products to cart (headless with session persistence)", 
            "/get-cart - Get cart contents (headless)",
            "/show-cart - Open visible browser to show cart with all your items",
            "/clear-cart-session - Clear saved cart session (start fresh)",
            "/health - Health check",
            "/docs - API documentation"
        ]
    }

@app.post("/search", response_model=SearchResponse)
async def search_shufersal(request: SearchRequest):
    """
    Simple step 1: Navigate to Shufersal, search, and get content
    """
    logger.info(f"🔍 Step 1: Simple search for '{request.search_term}'")
    
    try:
        # Get browser and create page
        browser_instance = await get_browser()
        page = await browser_instance.new_page()
        logger.info("✅ Browser page created (headless mode)")
        
        # Step 1: Navigate to Shufersal
        await page.goto("https://www.shufersal.co.il/online", timeout=30000)
        logger.info("✅ Navigated to Shufersal")
        
        # Step 2: Find search selector
        search_selector = 'input[placeholder*="חיפוש פריט, קטגוריה או מותג"]'
        await page.wait_for_selector(search_selector, timeout=10000)
        logger.info("✅ Found search input")
        
        # Step 3: Put the search term
        await page.fill(search_selector, request.search_term)
        logger.info(f"✅ Filled search term: '{request.search_term}'")
        
        # Step 4: Click search (press Enter)
        await page.press(search_selector, 'Enter')
        logger.info("✅ Clicked search")
        
        # # Step 5: Wait a bit for results
        # await page.wait_for_timeout(3000)  # Wait 3 seconds for initial results
        # logger.info("✅ Waited for initial results")
        
        # Step 6: Scroll 5 times to load more products
        logger.info("🔄 Step 3: Scrolling 5 times to load more products...")
        for scroll_num in range(5):
            logger.info(f"📜 Scroll {scroll_num + 1}/5")
            
            # Count products before scroll
            products_before = await page.query_selector_all('li.SEARCH.tileBlock')
            count_before = len(products_before)
            
            # Scroll to bottom
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            
            # Wait for new products to load
            await page.wait_for_timeout(2000)
            
            # Count products after scroll
            products_after = await page.query_selector_all('li.SEARCH.tileBlock')
            count_after = len(products_after)
            
            logger.info(f"✅ Scroll {scroll_num + 1}: {count_before} → {count_after} products")
            
            # If no new products loaded, break early
            if count_after == count_before:
                logger.info(f"🛑 No new products after scroll {scroll_num + 1}, stopping")
                break
        
        # Step 7: Get final content after all scrolls
        content = await page.content()
        search_url = page.url
        logger.info(f"✅ Got final content: {len(content)} characters")
        logger.info(f"✅ Search URL: {search_url}")
        
        # Step 8: Parse the content to extract products
        logger.info("🔍 Step 4: Parsing final content for products...")
        products = parse_shufersal_products(content, "https://www.shufersal.co.il")
        logger.info(f"✅ Parsed {len(products)} products from final content")
        
        # Return response with parsed products
        return SearchResponse(
            success=True,
            search_term=request.search_term,
            products=products,
            total_found=len(products),
            search_url=search_url,
            metadata={
                "content_length": len(content),
                "step": "2 - Search and parsing completed"
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Step 1 failed: {e}")
        return SearchResponse(
            success=False,
            search_term=request.search_term,
            products=[],
            total_found=0,
            search_url="",
            error=f"Step 1 failed: {str(e)}"
        )
    finally:
        # Always cleanup page (but keep browser for reuse)
        try:
            if page:
                await page.close()
                logger.debug("🔒 Page closed")
        except Exception as cleanup_error:
            logger.debug(f"⚠️ Error closing page: {cleanup_error}")    

    """Simple test to check if browser window is visible"""
    playwright_instance = None
    browser = None
    page = None
    
    try:
        logger.info("🧪 TESTING BROWSER VISIBILITY...")
        playwright_instance = await async_playwright().start()
        
        logger.info("🚀 Launching VISIBLE Chrome browser (using system Chrome)...")
        browser = await playwright_instance.chromium.launch(
            headless=False,
            slow_mo=2000,  # Very slow for visibility
            channel="chrome",  # Use system Chrome instead of Chromium
            args=['--no-sandbox', '--start-maximized']
        )
        
        page = await browser.new_page()
        logger.info("📄 Opening Google for 15 seconds...")
        
        await page.goto("https://www.google.com")
        await page.wait_for_timeout(15000)  # Keep open for 15 seconds
        
        logger.info("✅ Browser visibility test completed!")
        
        return {
            "success": True,
            "message": "Browser should have been visible for 15 seconds showing Google",
            "instructions": "Check if you saw a Chrome window open with Google"
        }
        
    except Exception as e:
        logger.error(f"❌ Browser visibility test failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Browser visibility test failed"
        }
    finally:
        try:
            if page: await page.close()
            if browser: await browser.close()
            if playwright_instance: await playwright_instance.stop()
        except:
            pass

    """Add to cart using a completely fresh browser instance"""
    logger.info(f"🛒 Fresh add to cart: {request.product_name} x{request.quantity}")
    
    playwright_instance = None
    browser = None
    page = None
    
    try:
        # Create completely fresh instances
        logger.info("🚀 Creating fresh Playwright instance...")
        playwright_instance = await async_playwright().start()
        
        logger.info("🚀 Launching VISIBLE Chrome browser (using system Chrome)...")
        browser = await playwright_instance.chromium.launch(
            headless=False,  # Make visible for testing
            slow_mo=1000,   # Slow down actions so you can see them
            channel="chrome",  # Use system Chrome instead of Chromium
            args=['--no-sandbox', '--start-maximized']  # Start maximized for better visibility
        )
        logger.info("✅ Browser launched successfully - you should see a Chrome window!")
        
        page = await browser.new_page()
        logger.info("📄 New page created - browser should be visible now!")
        
        # Navigate to search results or search page
        if request.search_url:
            await page.goto(request.search_url)
            await page.wait_for_timeout(3000)
            logger.info(f"✅ Loaded search results from URL")
        else:
            # Go to Shufersal and search
            await page.goto("https://www.shufersal.co.il/online/he/")
            await page.wait_for_selector('input[placeholder*="חיפוש"]', timeout=10000)
            await page.fill('input[placeholder*="חיפוש"]', request.product_name)
            await page.press('input[placeholder*="חיפוש"]', 'Enter')
            await page.wait_for_timeout(3000)
            logger.info(f"✅ Searched for product")
        
        # Find product by code
        target_tile = await page.query_selector(f'li[data-product-code="{request.product_code}"]')
        if not target_tile:
            raise Exception(f"Product not found: {request.product_code}")
        
        logger.info(f"✅ Found product tile")
        
        # Set quantity
        quantity_input = await target_tile.query_selector('input.js-qty-selector-input')
        if quantity_input:
            current_value = float(await quantity_input.get_attribute('value') or "0")
            target_quantity = float(request.quantity)
            
            if target_quantity > current_value:
                plus_button = await target_tile.query_selector('button.bootstrap-touchspin-up')
                if plus_button:
                    difference = target_quantity - current_value
                    increment = float(await quantity_input.get_attribute('data-inc') or "1")
                    clicks = int(round(difference / increment))
                    for _ in range(clicks):
                        await plus_button.click()
                        await page.wait_for_timeout(200)
                    logger.info(f"✅ Set quantity to {target_quantity}")
        
        # Click add to cart
        add_button = await target_tile.query_selector('button.js-add-to-cart')
        if add_button:
            await add_button.click()
            await page.wait_for_timeout(3000)
            logger.info("✅ Clicked add to cart")
            
            # Check for update button
            update_button = await target_tile.query_selector('button.js-update-cart')
            success = update_button is not None
            
            if success:
                logger.info("🎉 SUCCESS! Update button found")
                
                # Navigate to cart to show the result (for visible testing)
                try:
                    await page.goto("https://www.shufersal.co.il/online/he/cart")
                    await page.wait_for_timeout(5000)  # Wait longer to see the cart
                    logger.info("🛒 Navigated to cart page for verification")
                    
                    # Keep browser open for 15 seconds so user can see the result
                    logger.info("⏰ Keeping browser open for 15 seconds so you can see the cart...")
                    await page.wait_for_timeout(15000)
                    
                except Exception as cart_error:
                    logger.warning(f"⚠️ Could not navigate to cart: {cart_error}")
                    
            else:
                logger.warning("⚠️ Update button not found")
            
            return AddToCartResponse(
                success=success,
                product_code=request.product_code,
                quantity=request.quantity,
                message=f"{'Successfully added' if success else 'Attempted to add'} {request.quantity} x {request.product_name} to cart"
            )
        else:
            raise Exception("Add to cart button not found")
            
    except Exception as e:
        logger.error(f"❌ Fresh add to cart error: {e}")
        return AddToCartResponse(
            success=False,
            product_code=request.product_code,
            quantity=request.quantity,
            message=f"Failed to add product to cart",
            error=str(e)
        )
    finally:
        # Always cleanup
        try:
            if page:
                await page.close()
            if browser:
                await browser.close()
            if playwright_instance:
                await playwright_instance.stop()
        except:
            pass

@app.get("/get-cart")
async def get_cart():
    """Get current cart contents (headless)"""
    try:
        browser_instance = await get_browser()
        page = await browser_instance.new_page()
        
        try:
            # Navigate to cart page
            cart_url = "https://www.shufersal.co.il/"
            await page.goto(cart_url)
            await page.wait_for_timeout(3000)
            
            # Get cart items
            cart_items = []
            try:
                # Look for cart item elements
                items = await page.query_selector_all('.cart-item, .cartItem, [class*="cart-item"], [class*="cartItem"]')
                
                for item in items:
                    try:
                        name_element = await item.query_selector('[data-product-name], .product-name, .item-name')
                        quantity_element = await item.query_selector('input[name="qty"], .quantity-input, .qty')
                        price_element = await item.query_selector('.price, .item-price')
                        
                        name = await name_element.inner_text() if name_element else "Unknown"
                        quantity = await quantity_element.get_attribute('value') if quantity_element else "1"
                        price = await price_element.inner_text() if price_element else "N/A"
                        
                        cart_items.append({
                            "name": name.strip(),
                            "quantity": quantity,
                            "price": price.strip()
                        })
                    except:
                        continue
                        
            except Exception as parse_error:
                logger.warning(f"⚠️ Could not parse cart items: {parse_error}")
            
            return {
                "success": True,
                "cart_url": cart_url,
                "items": cart_items,
                "item_count": len(cart_items),
                "message": f"Found {len(cart_items)} items in cart"
            }
            
        finally:
            await page.close()
            
    except Exception as e:
        logger.error(f"❌ Error getting cart: {e}")
        return {
            "success": False,
            "error": str(e),
            "cart_url": "https://www.shufersal.co.il/online/he/cart",
            "items": [],
            "item_count": 0
        }

def show_cart_sync():
    """Open a visible browser window to show the cart contents - sync version"""
    from playwright.sync_api import sync_playwright
    import os
    import json
    
    try:
        logger.info("🛒 Opening visible browser to show your cart...")
        
        # Session file path
        session_file = "shufersal_session.json"
        
        with sync_playwright() as p:
            # Launch VISIBLE browser for cart viewing
            logger.info("🚀 Launching VISIBLE Chrome browser for cart viewing...")
            browser = p.chromium.launch(
                headless=False,  # Make browser visible
                channel="chrome",  # Use system Chrome
                args=[
                    '--no-sandbox', 
                    '--start-maximized',  # Start maximized for better visibility
                ]
            )
            logger.info("✅ Visible browser launched - YOU SHOULD SEE A CHROME WINDOW!")
            
            # Load session state to maintain cart items
            logger.info("📂 Loading session state to show your cart items...")
            if os.path.exists(session_file):
                try:
                    with open(session_file, 'r') as f:
                        storage_state = json.load(f)
                    context = browser.new_context(storage_state=storage_state)
                    logger.info("✅ Session loaded - your cart items should be visible!")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to load session: {e}, showing empty cart")
                    context = browser.new_context()
            else:
                logger.warning("⚠️ No session found - cart may be empty")
                context = browser.new_context()
            
            page = context.new_page()
            
            # Navigate to cart page
            logger.info("📄 Navigating to cart page...")
            cart_url = "https://www.shufersal.co.il"
            page.goto(cart_url, timeout=30000)
            page.wait_for_timeout(3000)  # Wait for page to load
            
            logger.info("🛒 Cart page loaded - you should see your cart contents!")
            logger.info("⏰ Browser will stay open until you close it manually")
            logger.info("🖱️  You can interact with the cart, modify quantities, proceed to checkout, etc.")
            
            # Keep the browser open much longer so user can interact
            page.wait_for_timeout(60000)  # 60 seconds, but user can close anytime
            
            logger.info("✅ Cart viewing session completed!")
            
        return {
            "success": True,
            "message": "Cart browser opened successfully! You can interact with it.",
            "cart_url": cart_url,
            "instructions": "A Chrome window opened showing your cart. You can interact with it, modify items, or proceed to checkout."
        }
        
    except Exception as e:
        logger.error(f"❌ Error showing cart: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to show cart in visible browser"
        }

@app.get("/show-cart")
async def show_cart():
    """Open a visible browser window to show the cart contents - user can interact with it"""
    logger.info("🛒 User requested to see cart in browser...")
    
    try:
        # Run sync cart viewer in thread pool
        import asyncio
        import concurrent.futures
        
        logger.info("🚀 Opening cart browser in thread pool...")
        
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            result = await loop.run_in_executor(executor, show_cart_sync)
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error running cart viewer: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to open cart browser"
        }

@app.delete("/clear-cart-session")
async def clear_cart_session():
    """Clear the saved cart session (start fresh)"""
    import os
    
    try:
        session_file = "shufersal_session.json"
        if os.path.exists(session_file):
            os.remove(session_file)
            logger.info("🗑️ Cart session cleared successfully")
            return {
                "success": True,
                "message": "Cart session cleared. Next cart operations will start with empty cart."
            }
        else:
            return {
                "success": True,
                "message": "No cart session found to clear."
            }
    except Exception as e:
        logger.error(f"❌ Error clearing cart session: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to clear cart session"
        }

def run_sync_browser_test(items: List[Dict[str, Any]]):
    """
    Run sync playwright add-to-cart process in a separate function
    """
    from playwright.sync_api import sync_playwright
    import os
    import json
    
    try:
        logger.info("✅ Imported sync playwright")
        
        # Session file path
        session_file = "shufersal_session.json"
        
        # Use sync playwright context manager
        logger.info("🚀 Creating sync playwright context...")
        with sync_playwright() as p:
            logger.info("✅ Sync playwright context created")
            
            # Launch HEADLESS browser for fast processing
            logger.info("🚀 Launching HEADLESS Chrome browser for fast processing...")
            browser = p.chromium.launch(
                headless=False,   # Make it headless for speed
                channel="chrome",  # Use system Chrome instead of Chromium
            )
            logger.info("✅ Headless Chrome browser launched for fast processing")
            
            # Create browser context with session persistence
            logger.info("🚀 Creating browser context with session persistence...")
            
            # Try to load existing session
            if os.path.exists(session_file):
                logger.info("📂 Loading existing session state...")
                try:
                    with open(session_file, 'r') as f:
                        storage_state = json.load(f)
                    context = browser.new_context(storage_state=storage_state)
                    logger.info("✅ Session state loaded successfully")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to load session state: {e}, creating new session")
                    context = browser.new_context()
            else:
                logger.info("📂 No existing session found, creating new session...")
                context = browser.new_context()
            
            logger.info("✅ Browser context created with session management")
            
            # Open new page
            logger.info("🚀 Opening new page...")
            page = context.new_page()
            logger.info("✅ New page opened")
            
            # Process each item in the list
            results = []
            successful_items = 0
            failed_items = 0
            
            for i, item in enumerate(items):
                logger.info(f"🛒 Processing item {i+1}/{len(items)}: {item.get('product_name', 'Unknown')}")
                
                try:
                    # Open new page for each item (or reuse existing page)
                    if i == 0:
                        # Use the existing page for the first item
                        current_page = page
                    else:
                        # Create new page for subsequent items
                        current_page = context.new_page()
                    
                    # Extract item details
                    search_url = item.get('search_url')
                    product_name = item.get('product_name', '')
                    product_code = item.get('product_code', '')
                    quantity = float(item.get('quantity', 1))
                    
                    # Navigate to search URL or search for product
                    if search_url:
                        logger.info(f"🚀 Navigating to search URL: {search_url}")
                        current_page.goto(search_url, timeout=30000)
                        logger.info("✅ Loaded search results page from URL")
                        current_page.wait_for_timeout(2000)
                    else:
                        # Navigate to Shufersal and search for the product
                        logger.info("🚀 Navigating to Shufersal...")
                        current_page.goto("https://www.shufersal.co.il/online", timeout=30000)
                        logger.info("✅ Navigated to Shufersal homepage")
                        
                        # Search for the product
                        logger.info(f"🔍 Searching for product: {product_name}")
                        search_selector = 'input[placeholder*="חיפוש פריט, קטגוריה או מותג"]'
                        current_page.wait_for_selector(search_selector, timeout=10000)
                        current_page.fill(search_selector, product_name)
                        current_page.press(search_selector, 'Enter')
                        current_page.wait_for_timeout(3000)
                        logger.info(f"✅ Searched for product: {product_name}")
                    
                    # Find the specific product by product code
                    logger.info(f"🔍 Looking for product with code: {product_code}")
                    target_product_tile = current_page.query_selector(f'li[data-product-code="{product_code}"]')
                    
                    if not target_product_tile:
                        raise Exception(f"Could not find product tile with code: {product_code}")
                    
                    # Get the product name from the tile for logging
                    tile_product_name = target_product_tile.get_attribute('data-product-name')
                    logger.info(f"✅ Found target product tile: {tile_product_name} (Code: {product_code})")
                    
                    # Set the correct quantity
                    logger.info(f"🔢 Setting quantity to {quantity}")
                    
                    # Get the current quantity value from the input
                    quantity_input = target_product_tile.query_selector('input.js-qty-selector-input')
                    if not quantity_input:
                        raise Exception("Could not find quantity input")
                    
                    # Set the value directly in the input field
                    quantity_input.click()  # Focus on the input
                    quantity_input.fill("")  # Clear current value
                    quantity_input.fill(str(quantity))  # Set new value
                    quantity_input.press('Tab')  # Tab out to trigger change
                    current_page.wait_for_timeout(500)  # Wait for value to be processed
                    
                    # Verify the value was set
                    new_value = quantity_input.get_attribute('value')
                    logger.info(f"✅ Value set to: {new_value}")
                    
                    # Click the add to cart button
                    logger.info("🛒 Clicking add to cart button...")
                    add_button = target_product_tile.query_selector('button.js-add-to-cart')
                    if not add_button:
                        raise Exception("Could not find add to cart button")
                    
                    # Make sure the button is visible and clickable
                    add_button.scroll_into_view_if_needed()
                    current_page.wait_for_timeout(500)
                    
                    # Try to click the button
                    try:
                        add_button.click()
                        logger.info("✅ Clicked add to cart button")
                    except Exception as click_error:
                        logger.warning(f"⚠️ Normal click failed: {click_error}")
                        try:
                            add_button.click(force=True)
                            logger.info("✅ Clicked add to cart button (force click)")
                        except Exception as force_error:
                            current_page.evaluate("(button) => button.click()", add_button)
                            logger.info("✅ Clicked add to cart button (JavaScript click)")
                    
                    # Wait for response
                    current_page.wait_for_timeout(2000)
                    
                    # Close the page if it's not the main page
                    if i > 0:
                        current_page.close()
                    
                    # Mark as successful
                    successful_items += 1
                    logger.info(f"✅ Successfully added: {product_name}")
                    
                    results.append({
                        "success": True,
                        "product_code": product_code,
                        "quantity": quantity,
                        "product_name": product_name,
                        "message": f"Successfully added {quantity} x {product_name} to cart"
                    })
                    
                except Exception as e:
                    failed_items += 1
                    logger.error(f"❌ Error adding item {product_name}: {e}")
                    
                    results.append({
                        "success": False,
                        "product_code": item.get('product_code', ''),
                        "quantity": item.get('quantity', 0),
                        "product_name": item.get('product_name', ''),
                        "message": f"Failed to add {item.get('product_name', 'Unknown')} to cart",
                        "error": str(e)
                    })
                    
                    # Close page if it exists and it's not the main page
                    try:
                        if i > 0 and 'current_page' in locals():
                            current_page.close()
                    except:
                        pass
            
            # Save session state after all items
            logger.info("💾 Saving session state for future use...")
            try:
                storage_state = context.storage_state()
                with open(session_file, 'w') as f:
                    json.dump(storage_state, f, indent=2)
                logger.info("✅ Session state saved successfully")
            except Exception as e:
                logger.warning(f"⚠️ Failed to save session state: {e}")
        
        logger.info(f"🎉 Batch add to cart completed: {successful_items} successful, {failed_items} failed")
        
        return {
            "success": failed_items == 0,
            "total_items": len(items),
            "successful_items": successful_items,
            "failed_items": failed_items,
            "results": results,
            "message": f"Added {successful_items}/{len(items)} items to cart"
        }

        
    except Exception as e:
        logger.error(f"❌ Error in add to cart process: {e}")
        return {"success": False, "error": str(e)}

@app.post("/add-to-cart", response_model=AddToCartResponse)
async def add_to_cart(request: AddToCartRequest):
    """
    Add items to cart - supports both single item and array of items
    """
    try:
        # Prepare items list - support both single item and array
        items_to_process = []
        
        if request.items:
            # Array of items provided
            logger.info(f"🛒 Processing {len(request.items)} items from array")
            for item in request.items:
                items_to_process.append({
                    "product_code": item.product_code,
                    "quantity": item.quantity,
                    "product_name": item.product_name,
                    "search_url": item.search_url
                })
        elif request.product_code:
            # Single item provided (legacy support)
            logger.info(f"🛒 Processing single item: {request.product_name}")
            items_to_process.append({
                "product_code": request.product_code,
                "quantity": request.quantity,
                "product_name": request.product_name,
                "search_url": request.search_url
            })
        else:
            raise ValueError("Either 'items' array or single item fields (product_code, quantity) must be provided")
        
        # Run sync playwright in thread pool to avoid asyncio conflict
        import asyncio
        import concurrent.futures
        
        logger.info("🚀 Running sync playwright in thread pool...")
        
        # Run the sync function in a thread pool
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            result = await loop.run_in_executor(
                executor, 
                run_sync_browser_test, 
                items_to_process
            )
        
        # Process results
        if result["success"]:
            return AddToCartResponse(
                success=True,
                total_items=result["total_items"],
                successful_items=result["successful_items"],
                failed_items=result["failed_items"],
                results=[
                    CartItemResult(
                        success=r["success"],
                        product_code=r["product_code"],
                        quantity=r["quantity"],
                        product_name=r["product_name"],
                        message=r["message"],
                        error=r.get("error")
                    ) for r in result["results"]
                ],
                message=f"Added {result['successful_items']}/{result['total_items']} items to cart. Use GET /show-cart to view your cart!"
            )
        else:
            return AddToCartResponse(
                success=False,
                total_items=result["total_items"],
                successful_items=result["successful_items"],
                failed_items=result["failed_items"],
                results=[
                    CartItemResult(
                        success=r["success"],
                        product_code=r["product_code"],
                        quantity=r["quantity"],
                        product_name=r["product_name"],
                        message=r["message"],
                        error=r.get("error")
                    ) for r in result["results"]
                ],
                message=result.get("message", "Some items failed to add"),
                error=result.get("error")
            )
        
    except Exception as e:
        logger.error(f"❌ Error in add to cart: {e}")
        return AddToCartResponse(
            success=False,
            total_items=0,
            successful_items=0,
            failed_items=0,
            results=[],
            message=f"Failed to process cart request: {str(e)}",
            error=str(e)
        )

# Additional utility endpoints
@app.get("/health")
async def health_check():
    """Health check with browser status"""
    global browser
    return {
        "status": "healthy",
        "browser_ready": browser is not None,
        "timestamp": int(time.time())
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
