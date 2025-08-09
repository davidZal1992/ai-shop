"""
Step 1 Improved: Shufersal Scraper with specific HTML structure parsing
Based on the actual HTML structure you found
"""
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time
from loguru import logger
import json

def extract_product_info(product_li):
    """
    Extract all product information from a single <li> element
    Based on the actual Shufersal HTML structure
    """
    try:
        # Extract data attributes from the <li> element
        product_name = product_li.get('data-product-name', '')
        product_price = product_li.get('data-product-price', '')
        product_code = product_li.get('data-product-code', '')
        is_purchasable = product_li.get('data-product-purchasable', 'false') == 'true'
        selling_method = product_li.get('data-selling-method', '')
        
        # Extract additional info from within the HTML
        soup_li = BeautifulSoup(str(product_li), 'html.parser')
        
        # Get product description from the strong tag
        description_elem = soup_li.find('strong')
        description = description_elem.get_text(strip=True) if description_elem else product_name
        
        # Get brand name
        brand_elem = soup_li.find('div', class_='brand-name')
        brand = ""
        if brand_elem:
            brand_spans = brand_elem.find_all('span')
            if len(brand_spans) >= 2:
                brand = brand_spans[1].get_text(strip=True)
        
        # Get price from the price span
        price_elem = soup_li.find('span', class_='number')
        price_text = price_elem.get_text(strip=True) if price_elem else product_price
        
        # Get image URL
        img_elem = soup_li.find('img', class_='pic')
        image_url = img_elem.get('src', '') if img_elem else ''
        
        # Check if on promotion
        promotion_elem = soup_li.find('div', class_='promotion-section')
        is_promotion = promotion_elem is not None
        
        # Check stock status
        out_of_stock_msg = soup_li.find('div', class_='miglog-prod-outOfStock-msg')
        low_stock_msg = soup_li.find('div', class_='miglog-prod-lowStock-msg')
        
        stock_status = "in_stock"
        if out_of_stock_msg and out_of_stock_msg.get_text(strip=True):
            stock_status = "out_of_stock"
        elif low_stock_msg and low_stock_msg.get_text(strip=True):
            stock_status = "low_stock"
        
        # Get unit information
        unit_info = ""
        unit_pick = soup_li.find('span', class_='unitPick')
        if unit_pick:
            unit_labels = unit_pick.find_all('span', class_='miglog-sm-label')
            for label in unit_labels:
                unit_text = label.get_text(strip=True)
                if unit_text:
                    unit_info = unit_text
                    break
        
        return {
            'name': description or product_name,
            'product_code': product_code,
            'price': price_text,
            'brand': brand,
            'image_url': image_url,
            'is_promotion': is_promotion,
            'stock_status': stock_status,
            'is_purchasable': is_purchasable,
            'selling_method': selling_method,
            'unit_info': unit_info
        }
        
    except Exception as e:
        logger.error(f"Error extracting product info: {e}")
        return None

def search_shufersal_improved(search_term: str):
    """
    Improved Shufersal search using the specific HTML structure
    """
    logger.info(f"🔍 Searching Shufersal for: {search_term}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=1000)
        page = browser.new_page()
        
        try:
            # Navigate to Shufersal online
            logger.info("📱 Opening Shufersal online...")
            page.goto("https://www.shufersal.co.il/online", timeout=60000)
            
            # Wait for page to load
            page.wait_for_load_state("domcontentloaded")
            time.sleep(5)
            
            logger.info(f"📍 Current URL: {page.url}")
            
            # Find and use search box
            logger.info(f"🔍 Searching for: {search_term}")
            
            # Try different search selectors
            search_selectors = [
                'input[type="search"]',
                'input[placeholder*="חיפוש"]',
                '.search-input',
                '#search',
                'input[name="search"]'
            ]
            
            search_success = False
            for selector in search_selectors:
                try:
                    search_box = page.wait_for_selector(selector, timeout=5000)
                    if search_box:
                        logger.info(f"✅ Found search box with: {selector}")
                        search_box.fill(search_term)
                        search_box.press("Enter")
                        search_success = True
                        break
                except:
                    continue
            
            if not search_success:
                logger.error("❌ Could not find search box")
                return []
            
            # Wait for search results
            logger.info("⏳ Waiting for search results...")
            page.wait_for_load_state("networkidle", timeout=30000)
            time.sleep(5)
            
            # Take screenshot of results
            page.screenshot(path="search_results.png", full_page=True)
            logger.info("📸 Search results screenshot saved")
            
            # Get page content
            content = page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Look for product list items with the specific structure
            logger.info("🔍 Looking for product items...")
            
            # Find all <li> elements with class "SEARCH tileBlock"
            product_items = soup.find_all('li', class_=lambda x: x and 'SEARCH' in x and 'tileBlock' in x)
            
            if not product_items:
                logger.warning("⚠️ No product items found with expected structure")
                # Fallback: look for any <li> with data-product-name
                product_items = soup.find_all('li', attrs={'data-product-name': True})
            
            logger.info(f"✅ Found {len(product_items)} product items")
            
            # Extract information from each product
            products = []
            for i, item in enumerate(product_items, 1):
                logger.info(f"📦 Processing product {i}/{len(product_items)}")
                
                product_info = extract_product_info(item)
                if product_info:
                    products.append(product_info)
                    logger.info(f"✅ Extracted: {product_info['name']} - ₪{product_info['price']}")
            
            # Print results
            print(f"\n🛒 SEARCH RESULTS FOR '{search_term}':")
            print("=" * 80)
            print(f"Found {len(products)} products:")
            print()
            
            for i, product in enumerate(products, 1):
                print(f"{i}. {product['name']}")
                print(f"   💰 Price: ₪{product['price']}")
                print(f"   🏷️  Brand: {product['brand']}")
                print(f"   📦 Product Code: {product['product_code']}")
                print(f"   📊 Stock: {product['stock_status']}")
                print(f"   🛒 Purchasable: {'Yes' if product['is_purchasable'] else 'No'}")
                print(f"   🎯 Promotion: {'Yes' if product['is_promotion'] else 'No'}")
                print(f"   📏 Unit: {product['unit_info']}")
                print(f"   🖼️  Image: {product['image_url'][:50]}..." if product['image_url'] else "   🖼️  Image: None")
                print("-" * 40)
            
            # Save results to JSON file
            with open('search_results.json', 'w', encoding='utf-8') as f:
                json.dump(products, f, ensure_ascii=False, indent=2)
            logger.info("💾 Results saved to search_results.json")
            
            return products
            
        except Exception as e:
            logger.error(f"❌ Error during scraping: {e}")
            page.screenshot(path="error_screenshot.png", full_page=True)
            logger.info("📸 Error screenshot saved")
            return []
        
        finally:
            browser.close()
            logger.info("🔒 Browser closed")

if __name__ == "__main__":
    # Test with מלפפון (cucumber)
    search_term = " 250גבינה צהובה 9 אחוז מהמעדניה"
    
    print("🚀 Starting Improved Shufersal Scraper")
    print(f"🔍 Searching for: {search_term}")
    print("-" * 50)
    
    results = search_shufersal_improved(search_term)
    
    print(f"\n✅ Scraping completed!")
    print(f"📊 Total products found: {len(results)}")
    print("📁 Check search_results.json for detailed data")
    print("📸 Check search_results.png for visual confirmation")
