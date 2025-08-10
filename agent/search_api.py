"""
Simultaneous Product Search API - FastAPI server for efficient product search with crawl4ai
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import asyncio
import json
from loguru import logger
import sys

from crawl4ai import AsyncWebCrawler
import webbrowser
import subprocess

# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="DEBUG",
    colorize=True
)

app = FastAPI(
    title="Simultaneous Product Search API",
    description="Search multiple products simultaneously using crawl4ai",
    version="1.0.0"
)

# Request Models
class SearchItem(BaseModel):
    name: str
    quantity: float
    brand: Optional[str] = None
    unit: Optional[str] = None
    preferences: Optional[str] = None

class SimultaneousSearchRequest(BaseModel):
    items: List[SearchItem]
    max_scrolls: Optional[int] = 3
    max_candidates: Optional[int] = 40

# Add to Cart Models
class CartItem(BaseModel):
    name: str
    product_code: str
    quantity: float

class AddToCartRequest(BaseModel):
    items: List[CartItem]

class CartItemResult(BaseModel):
    success: bool
    name: str
    product_code: str
    quantity: float
    message: str
    error: Optional[str] = None

class AddToCartResponse(BaseModel):
    success: bool
    total_items: int
    successful_items: int
    failed_items: int
    results: List[CartItemResult]
    message: str
    cart_url: str
    error: Optional[str] = None

# Response Models
class Candidate(BaseModel):
    name: str
    unit: Optional[str] = None
    promotion: Optional[str] = None
    price: float
    product_code: Optional[str] = None

class SearchItemResult(BaseModel):
    name: str
    quantity: float
    brand: Optional[str] = None
    unit: Optional[str] = None
    preferences: Optional[str] = None
    candidates: List[Candidate] = []

class SimultaneousSearchResponse(BaseModel):
    success: bool
    results: List[SearchItemResult] = []
    total_items: int = 0
    error: Optional[str] = None

async def search_single_item_with_crawl4ai(item: SearchItem, max_scrolls: int = 3, max_candidates: int = 40) -> SearchItemResult:
    """
    Search for a single item using crawl4ai with pagination
    """
    try:
        logger.info(f"🔍 Searching for item: {item.name}")
        
        async with AsyncWebCrawler(verbose=True) as crawler:
            # Navigate to Shufersal and perform search
            # Include brand in search query if available
            search_query = item.name
            if item.brand:
                search_query = f"{item.name} {item.brand}"
            
            search_url = f"https://www.shufersal.co.il/online/he/search?q={search_query.replace(' ', '%20')}"
            
            # Initial page load
            result = await crawler.arun(
                url=search_url,
                wait_for="css:li.SEARCH.tileBlock",
                timeout=30000
            )
            
            candidates = []
            
            # Extract products from initial load
            if result.success:
                initial_products = parse_products_from_html(result.html)
                candidates.extend(initial_products)
                logger.info(f"✅ Initial load: Found {len(initial_products)} products for {item.name}")
            
            # Perform scrolling to get more products
            for scroll in range(max_scrolls):
                if len(candidates) >= max_candidates:
                    break
                    
                logger.info(f"📜 Scroll {scroll + 1}/{max_scrolls} for {item.name}")
                
                # Scroll down and wait for new content
                scroll_result = await crawler.arun(
                    url=search_url,
                    js_code="""
                    window.scrollTo(0, document.body.scrollHeight);
                    await new Promise(resolve => setTimeout(resolve, 2000));
                    """,
                    wait_for="css:li.SEARCH.tileBlock",
                    timeout=15000
                )
                
                if scroll_result.success:
                    new_products = parse_products_from_html(scroll_result.html)
                    # Filter out duplicates
                    existing_names = {c.name for c in candidates}
                    unique_new_products = [p for p in new_products if p.name not in existing_names]
                    candidates.extend(unique_new_products)
                    logger.info(f"✅ Scroll {scroll + 1}: Added {len(unique_new_products)} new products")
                else:
                    logger.warning(f"⚠️ Scroll {scroll + 1} failed for {item.name}")
            
            # Limit candidates to max_candidates
            candidates = candidates[:max_candidates]
            
            return SearchItemResult(
                name=item.name,
                quantity=item.quantity,
                brand=item.brand,
                unit=item.unit,
                preferences=item.preferences,
                candidates=candidates
            )
            
    except Exception as e:
        logger.error(f"❌ Error searching for {item.name}: {e}")
        return SearchItemResult(
            name=item.name,
            quantity=item.quantity,
            brand=item.brand,
            unit=item.unit,
            preferences=item.preferences,
            candidates=[]
        )

def parse_products_from_html(html_content: str) -> List[Candidate]:
    """
    Parse HTML content and extract product candidates
    """
    from bs4 import BeautifulSoup
    import re
    
    candidates = []
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find all product items
    product_items = soup.find_all('li', class_=lambda x: x and 'SEARCH' in x and 'tileBlock' in x)
    
    for item in product_items:
        try:
            # Extract basic product data
            product_name = item.get('data-product-name', '').strip()
            product_price = item.get('data-product-price', '0')
            product_code = item.get('data-product-code', '').strip()
            
            if not product_name:
                continue
            
            # Convert price to float
            try:
                price = float(product_price)
            except (ValueError, TypeError):
                price = 0.0
            
            # Extract unit
            unit = None
            unit_pick = item.find('span', class_='unitPick')
            if unit_pick:
                unit = unit_pick.get_text(strip=True)
            
            # Extract promotion
            promotion = None
            promotion_div = item.find('div', class_='promotion-section')
            if promotion_div:
                promotion_text = promotion_div.find('strong')
                if promotion_text:
                    promotion = promotion_text.get_text(strip=True)
                    promotion = re.sub(r'\s+', ' ', promotion)
            
            candidate = Candidate(
                name=product_name,
                unit=unit,
                promotion=promotion,
                price=price,
                product_code=product_code
            )
            
            candidates.append(candidate)
            
        except Exception as e:
            logger.warning(f"⚠️ Error parsing product item: {e}")
            continue
    
    return candidates

async def add_items_to_cart_with_session(items: List[CartItem]) -> List[CartItemResult]:
    """
    Add multiple items to cart using Playwright with session persistence and visible browser
    """
    try:
        logger.info(f"🛒 Adding {len(items)} items to cart with session persistence")
        
        results = []
        
        # Use Playwright with visible browser
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,  # Visible browser
                channel="chrome",
                args=['--no-sandbox', '--start-maximized']
            )
            
            # Try to load existing session
            try:
                with open("shufersal_session.json", 'r', encoding='utf-8') as f:
                    storage_state = json.load(f)
                context = browser.new_context(storage_state=storage_state)
                logger.info("✅ Loaded existing session")
            except:
                context = browser.new_context()
                logger.info("ℹ️ Starting new session")
            
            page = context.new_page()
            # Navigate to homepage first to establish session
            logger.info("🌐 Navigating to Shufersal homepage...")
            await crawler.arun(
                url="https://www.shufersal.co.il/online",
                wait_for="body",
                timeout=30000
            )
            
            # Process each item
            for item in items:
                try:
                    logger.info(f"🛒 Processing: {item.name} (Code: {item.product_code})")
                    
                    # Search for the product
                    search_url = f"https://www.shufersal.co.il/online/he/search?q={item.name.replace(' ', '%20')}"
                    
                    search_result = await crawler.arun(
                        url=search_url,
                        wait_for="css:li.SEARCH.tileBlock",
                        timeout=30000
                    )
                    
                    if not search_result.success:
                        raise Exception("Failed to load search results")
                    
                    # Add to cart with JavaScript
                    js_code = f"""
                    // Find the product tile
                    const productTile = document.querySelector('li[data-product-code="{item.product_code}"]');
                    if (!productTile) {{
                        throw new Error('Product not found with code: {item.product_code}');
                    }}
                    
                    // Scroll to product
                    productTile.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                    await new Promise(resolve => setTimeout(resolve, 1000));
                    
                    // Set quantity
                    const quantityInput = productTile.querySelector('input.js-qty-selector-input');
                    if (quantityInput) {{
                        quantityInput.focus();
                        quantityInput.select();
                        quantityInput.value = '{item.quantity}';
                        quantityInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        quantityInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        await new Promise(resolve => setTimeout(resolve, 500));
                    }}
                    
                    // Find and click add to cart button
                    const addButton = productTile.querySelector('button.js-add-to-cart, .js-add-to-cart');
                    if (!addButton) {{
                        throw new Error('Add to cart button not found');
                    }}
                    
                    // Make sure button is visible and enabled
                    addButton.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                    await new Promise(resolve => setTimeout(resolve, 1000));
                    
                    // Try multiple click methods
                    let clicked = false;
                    try {{
                        addButton.click();
                        clicked = true;
                    }} catch (e1) {{
                        try {{
                            addButton.dispatchEvent(new MouseEvent('click', {{ 
                                bubbles: true, 
                                cancelable: true,
                                view: window 
                            }}));
                            clicked = true;
                        }} catch (e2) {{
                            // Force click with JavaScript
                            if (addButton.onclick) {{
                                addButton.onclick();
                            }} else {{
                                addButton.click();
                            }}
                            clicked = true;
                        }}
                    }}
                    
                    if (!clicked) {{
                        throw new Error('Failed to click add to cart button');
                    }}
                    
                    // Wait for cart update
                    await new Promise(resolve => setTimeout(resolve, 3000));
                    
                    // Check if item was added (look for cart badge update or success message)
                    console.log('Item added to cart:', '{item.name}');
                    """
                    
                    # Execute the add to cart action
                    cart_result = await crawler.arun(
                        url=search_url,
                        js_code=js_code,
                        wait_for="css:li.SEARCH.tileBlock",
                        timeout=30000
                    )
                    
                    if cart_result.success:
                        results.append(CartItemResult(
                            success=True,
                            name=item.name,
                            product_code=item.product_code,
                            quantity=item.quantity,
                            message=f"Successfully added {item.quantity} x {item.name} to cart"
                        ))
                        logger.info(f"✅ Successfully added {item.name}")
                    else:
                        raise Exception("Failed to execute add to cart")
                        
                except Exception as e:
                    logger.error(f"❌ Error adding {item.name}: {e}")
                    results.append(CartItemResult(
                        success=False,
                        name=item.name,
                        product_code=item.product_code,
                        quantity=item.quantity,
                        message=f"Failed to add {item.name} to cart",
                        error=str(e)
                    ))
            
            # After all items are processed, navigate to cart to show results
            logger.info("🛒 Navigating to cart to show added items...")
            try:
                cart_result = await crawler.arun(
                    url="https://www.shufersal.co.il/online/he/cart",
                    wait_for="body",
                    timeout=30000
                )
                if cart_result.success:
                    logger.info("✅ Cart page loaded successfully - you should see your items!")
                    logger.info("🔒 Browser window will remain open indefinitely - you can continue shopping!")
                    logger.info("💡 Close the browser window manually when you're done")
                    
                    # Add a very long sleep to keep browser open - will be interrupted when user stops API
                    await asyncio.sleep(3600)  # 1 hour
                    
                else:
                    logger.warning("⚠️ Failed to load cart page")
            except Exception as cart_error:
                logger.warning(f"⚠️ Could not navigate to cart: {cart_error}")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Error in cart session: {e}")
        # Return failed results for all items
        return [CartItemResult(
            success=False,
            name=item.name,
            product_code=item.product_code,
            quantity=item.quantity,
            message=f"Failed to add {item.name} to cart",
            error=str(e)
        ) for item in items]

@app.post("/add-to-cart", response_model=AddToCartResponse)
async def add_to_cart(request: AddToCartRequest):
    """
    Add multiple items to cart simultaneously
    """
    try:
        logger.info(f"🛒 Starting add to cart for {len(request.items)} items")
        
        # Use session-based approach to add all items
        cart_results = await add_items_to_cart_with_session(request.items)
        
        # Process results
        successful_items = sum(1 for r in cart_results if r.success)
        failed_items = len(cart_results) - successful_items
        
        logger.info(f"🎉 Add to cart completed: {successful_items} successful, {failed_items} failed")
        
        # Browser window is already visible from crawl4ai (headless=False)
        homepage_url = "https://www.shufersal.co.il/online/"
        logger.info("🌐 Browser window should be visible with your items added to cart")
        logger.info("💡 The browser window will remain open - navigate to cart to see your items or check the cart icon")
        
        return AddToCartResponse(
            success=failed_items == 0,
            total_items=len(request.items),
            successful_items=successful_items,
            failed_items=failed_items,
            results=cart_results,
            message=f"Added {successful_items}/{len(request.items)} items to cart. Browser opened to homepage!",
            cart_url=homepage_url
        )
        
    except Exception as e:
        logger.error(f"❌ Add to cart error: {e}")
        return AddToCartResponse(
            success=False,
            total_items=len(request.items),
            successful_items=0,
            failed_items=len(request.items),
            results=[],
            message="Failed to process add to cart request",
            cart_url="https://www.shufersal.co.il/online/he/cart",
            error=str(e)
        )

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Simultaneous Product Search API is running",
        "version": "1.0.0",
        "endpoints": [
            "/search - Search multiple products simultaneously",
            "/add-to-cart - Add multiple products to cart",
            "/health - Health check"
        ]
    }

@app.post("/search", response_model=SimultaneousSearchResponse)
async def simultaneous_search(request: SimultaneousSearchRequest):
    """
    Search for multiple items simultaneously and return candidates for each
    """
    try:
        logger.info(f"🚀 Starting simultaneous search for {len(request.items)} items")
        
        # Create search tasks for all items
        search_tasks = []
        for item in request.items:
            task = search_single_item_with_crawl4ai(
                item, 
                max_scrolls=request.max_scrolls or 3,
                max_candidates=request.max_candidates or 40
            )
            search_tasks.append(task)
        
        # Execute all searches concurrently
        logger.info(f"⚡ Running {len(search_tasks)} searches concurrently...")
        results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        # Process results
        search_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"❌ Search failed for item {i}: {result}")
                # Create empty result for failed search
                failed_item = request.items[i]
                search_results.append(SearchItemResult(
                    name=failed_item.name,
                    quantity=failed_item.quantity,
                    brand=failed_item.brand,
                    unit=failed_item.unit,
                    preferences=failed_item.preferences,
                    candidates=[]
                ))
            else:
                search_results.append(result)
                logger.info(f"✅ Found {len(result.candidates)} candidates for {result.name}")
        
        total_candidates = sum(len(result.candidates) for result in search_results)
        logger.info(f"🎉 Search completed: {total_candidates} total candidates found")
        
        return SimultaneousSearchResponse(
            success=True,
            results=search_results,
            total_items=len(request.items)
        )
        
    except Exception as e:
        logger.error(f"❌ Simultaneous search error: {e}")
        return SimultaneousSearchResponse(
            success=False,
            results=[],
            total_items=len(request.items),
            error=str(e)
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": asyncio.get_event_loop().time()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)