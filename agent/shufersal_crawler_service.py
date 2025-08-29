import asyncio
import json
from crawl4ai import AsyncWebCrawler
from playwright.async_api import async_playwright


async def login_to_shufersal(page, username, password):
    """
    Login to Shufersal website
    """
    await page.goto("https://www.shufersal.co.il/online/he/login")
    await page.wait_for_selector("#j_username", timeout=10000)

    await page.fill("#j_username", username)
    await page.fill("#j_password", password)

    # Click login button
    try:
        await page.click("text=כניסה", timeout=5000)
    except:
        button_selectors = [
            "button:has-text('כניסה')",
            "input[type='submit']",
            "button[type='submit']"
        ]

        for selector in button_selectors:
            try:
                await page.click(selector, timeout=2000)
                break
            except:
                continue
        else:
            await page.keyboard.press("Enter")

    await page.wait_for_timeout(3000)

    if "/login" in page.url:
        raise Exception("Login failed")

    return True


async def extract_product_details(product_element):
    """
    Extract detailed information from a product element
    """
    try:
        # Basic product info
        product_code = await product_element.get_attribute("data-product-code")
        price = await product_element.get_attribute("data-product-price")

        # Extract full product name from description
        name = ""
        try:
            name_element = await product_element.query_selector(".text.description strong")
            if name_element:
                name = await name_element.inner_text()
        except:
            pass

        # Extract unit_size and brand from labelsListContainer
        unit_size = None
        brand = None
        try:
            spans = await product_element.query_selector_all(".labelsListContainer .smallText span")
            if len(spans) >= 1:
                unit_size = await spans[0].inner_text()
            if len(spans) > 1:
                brand = await spans[-1].inner_text()
        except:
            pass

        # Extract unit information
        unit = "יח'"
        unit_price = float(price) if price else 0
        try:
            unit_element = await product_element.query_selector(".unitPick span[aria-hidden='true']")
            if unit_element:
                unit = await unit_element.inner_text()
        except:
            pass

        # Extract promotion details (simple text only)
        promotion = None
        try:
            promotion_element = await product_element.query_selector(".promotion-section .productInnerPromotion .subText strong")
            if promotion_element:
                promotion = await promotion_element.inner_text()
        except:
            pass

        return {
            "name": name or "",
            "brand": brand,
            "price": float(price) if price else 0,
            "unit": unit,
            "unit_size": unit_size,
            "unit_price": unit_price,
            "product_code": product_code or "",
            "promotion": promotion
        }
    except Exception as e:
        print(f"Error extracting product details: {str(e)}")
        return None


async def extract_search_results(page):
    """
    Extract all product details from search results page
    """
    products = []
    try:
        # Wait for search results to load
        await page.wait_for_selector("li.SEARCH.tileBlock", timeout=5000)

        # Get all product elements
        product_elements = await page.query_selector_all("li.SEARCH.tileBlock")
        print(f"Found {len(product_elements)} products")

        for i, element in enumerate(product_elements):
            print(f"Extracting product {i + 1}...")
            product_details = await extract_product_details(element)
            if product_details:
                products.append(product_details)

        return products
    except Exception as e:
        print(f"Error extracting search results: {str(e)}")
        return []


async def search_product(page, product_name):
    """
    Search for a product and extract all results
    """
    search_input = await page.wait_for_selector("#js-site-search-input", timeout=10000)
    await search_input.fill(product_name)
    await page.keyboard.press("Enter")
    await page.wait_for_timeout(3000)

    # Extract and print all products from search results
    products = await extract_search_results(page)
    print(f"\n=== Search Results for '{product_name}' ===")
    print(json.dumps(products, ensure_ascii=False, indent=2))

    return products


async def add_to_cart_with_quantity(page, product_code, quantity):
    """
    Set quantity and add product to cart
    """
    # Set quantity
    await page.fill("input.js-qty-selector-input", str(quantity))

    # Click add to cart button
    try:
        await page.click(f'li[data-product-code="{product_code}"] button.js-add-to-cart', timeout=5000)
    except:
        try:
            await page.click('button:has-text("הוספה")', timeout=5000)
        except:
            await page.click('.js-add-to-cart', timeout=5000)

    await page.wait_for_timeout(2000)
    return True


async def shopping_flow(username, password, items=None):
    """
    Complete flow: login, search, and add to cart
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            # Login
            print("Logging in...")
            await login_to_shufersal(page, username, password)
            print("✅ Login successful")

            # Search for מלפפון
            print("Searching for מלפפון...")
            await search_product(page, "מלפפון")
            print("✅ Search completed")

            # Add 4.5 kg to cart
            print("Adding 4.5 kg מלפפון to cart...")
            await add_to_cart_with_quantity(page, "P_46", 4.5)
            print("✅ Added to cart")

            await browser.close()
            return {
                "success": True,
                "message": "Successfully added 4.5 kg מלפפון to cart"
            }
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            await browser.close()
            return {
                "success": False,
                "message": f"Error: {str(e)}"
            }


async def main():
    """
    Test the Shufersal automation
    """
    print("=== Shufersal Automation Test ===")

    username = "davidzal1992@gmail.com"
    password = "199214David"

    result = await shopping_flow(username, password)
    print(f"Result: {result['message']}")


if __name__ == "__main__":
    asyncio.run(main())
