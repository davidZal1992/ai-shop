import asyncio
import json
import openai
import os
from crawl4ai import AsyncWebCrawler
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()


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
            promotion_element = await product_element.query_selector(
                ".promotion-section .productInnerPromotion .subText strong")
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


async def search_single_product_in_tab(browser, product_name):
    """
    Search for a single product in a new tab and return candidates (no login needed)
    """
    page = await browser.new_page()
    try:
        # Navigate to main page (no login needed for search)
        await page.goto("https://www.shufersal.co.il/online/he")
        await page.wait_for_timeout(1000)

        # Search for the product
        print(f"Searching for '{product_name}'...")
        search_input = await page.wait_for_selector("#js-site-search-input", timeout=10000)
        await search_input.fill(product_name)
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(3000)

        # Extract candidates
        candidates = await extract_search_results(page)
        print(f"Found {len(candidates)} candidates for '{product_name}'")

        await page.close()
        return {
            "user_item": product_name,
            "candidates": candidates
        }

    except Exception as e:
        print(f"Error searching for '{product_name}': {str(e)}")
        await page.close()
        return {
            "user_item": product_name,
            "candidates": []
        }


async def search_in_tab(context, product_name):
    """
    Search for a single product in a new tab using browser context
    """
    page = await context.new_page()
    try:
        # Navigate to main page
        await page.goto("https://www.shufersal.co.il/online/he")
        await page.wait_for_timeout(1000)

        # Search for the product
        print(f"Searching for '{product_name}'...")
        search_input = await page.wait_for_selector("#js-site-search-input", timeout=10000)
        await search_input.fill(product_name)
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(3000)

        # Extract candidates
        candidates = await extract_search_results(page)
        print(f"Found {len(candidates)} candidates for '{product_name}'")

        await page.close()
        return {
            "user_item": product_name,
            "candidates": candidates
        }

    except Exception as e:
        print(f"Error searching for '{product_name}': {str(e)}")
        await page.close()
        return {
            "user_item": product_name,
            "candidates": []
        }


async def parallel_search_with_tabs(search_terms):
    """
    Run parallel searches for multiple products using ONE browser context with multiple tabs
    """
    print(f"Running parallel searches for: {search_terms}")

    async with async_playwright() as p:
        # Create ONE browser instance with context
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()

        try:
            # Create tasks for parallel execution using tabs from the SAME context
            tasks = [search_in_tab(context, term) for term in search_terms]

            # Run all searches in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Filter out any exceptions
            candidate_lists = []
            for result in results:
                if isinstance(result, dict):
                    candidate_lists.append(result)
                else:
                    print(f"Search error: {result}")

            await browser.close()
            return candidate_lists

        except Exception as e:
            print(f"Error in parallel search: {str(e)}")
            await browser.close()
            return []


async def find_best_matches_with_llm(candidate_lists):
    """
    Use LLM to find the best product matches from candidate lists
    """
    try:
        client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Create the prompt
        prompt = """You are an expert shopping assistant for an Israeli supermarket (Shufersal). Your task is to find the best product matches from search results.

MATCHING RULES:
1. **Name Match**: Find the most exact name match first
2. **Brand Match**: If user specifies a brand, prioritize that exact brand
3. **Preferences**: Consider specific user preferences (taste, organic, low-fat, etc.)
4. **Smart Promotions**: ALWAYS consider promotions and be smart about quantities:
   - "2 יח' ב- 30 ₪" = Buy 2 units for 30₪ → choose quantity 2
   - "3 ב- 45 ₪" = Buy 3 for 45₪ → choose quantity 3  
   - "קנה 2 קבל 1 חינם" = Buy 2 get 1 free → choose quantity 2
   - If promotion offers better value, adjust quantity accordingly
5. If you do not find a match, just set nulls and provide reason. 
6. Some products they are unit in weight and not boxed that you can pick them physically. If user Asked for example גבינה צהובה במשקל you should take 
in account the unit and understand that the item is not packed and this is item that we choose with weight.
7. Consider take small products if user asked, for example שקית קטנה ביסלי if you have match for 2 items but the user asked for the smallest look at unit_size of the product.

INPUT FORMAT:
For each user item, you'll receive candidates with: name, brand, price, unit_size, promotion, product_code

OUTPUT FORMAT:
Return ONLY a JSON array with this exact structure:
[
  {
    "user_item": "original search term",
    "product_name": "exact product name from candidates",
    "product_code": "exact product code",
    "quantity": number (can be decimal like 0.5, 1.5, 2.5 - consider promotions!),
    "reason": "brief explanation of choice and quantity reasoning"
  }
]

EXAMPLES:
- User searches "מלפפון חצי קילו" → Choose cucumber, quantity: 0.5 (half kilo). Convert it to correct number.
- User searches "ביסלי בצל" → Choose Bissli onion flavor, consider promotions
- If promotion is "2 יח' ב- 20 ₪" and regular price is 12₪ each → choose quantity 2 (saves 4₪)
- User searches "חלב 2 ליטר" → Choose milk, quantity: 2.0 (two liters)

BE SMART WITH PROMOTIONS - always calculate if the promotion quantity gives better value!

Here are the candidates:
"""

        prompt += json.dumps(candidate_lists, ensure_ascii=False, indent=2)
        
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": "Find the best matches for each item, being smart about promotions and quantities."}
            ]
        )
        
        # Parse the response
        matches_json = response.choices[0].message.content.strip()
        if matches_json.startswith("```json"):
            matches_json = matches_json.replace("```json", "").replace("```", "").strip()
        
        best_matches = json.loads(matches_json)
        return best_matches
        
    except Exception as e:
        print(f"Error in LLM matching: {str(e)}")
        # Fallback: return first candidate for each item
        fallback_matches = []
        for item_data in candidate_lists:
            if item_data['candidates']:
                candidate = item_data['candidates'][0]
                fallback_matches.append({
                    "user_item": item_data['user_item'],
                    "product_name": candidate['name'],
                    "product_code": candidate['product_code'],
                    "quantity": 1,
                    "reason": "Fallback match (LLM failed)"
                })
        return fallback_matches


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

async def add_product_to_cart_in_tab(context, best_match):
    """
    Search for a specific product and add it to cart in a new tab
    """
    page = await context.new_page()
    try:
        # Navigate to main page
        await page.goto("https://www.shufersal.co.il/online/he")
        await page.wait_for_timeout(1000)
        
        # Search for the specific product
        print(f"Searching for '{best_match['product_name']}'...")
        search_input = await page.wait_for_selector("#js-site-search-input", timeout=10000)
        await search_input.fill(best_match['product_name'])
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(3000)
        
        # Add to cart with quantity
        print(f"Adding {best_match['quantity']} to cart...")
        await page.fill("input.js-qty-selector-input", str(best_match['quantity']))
        
        # Click add to cart button for this specific product
        try:
            await page.click(f'li[data-product-code="{best_match["product_code"]}"] button.js-add-to-cart', timeout=5000)
        except:
            try:
                await page.click('button:has-text("הוספה")', timeout=5000)
            except:
                await page.click('.js-add-to-cart', timeout=5000)
        
        await page.wait_for_timeout(2000)
        print(f"✅ Added {best_match['product_name']} to cart")
        
        await page.close()
        return {
            "success": True,
            "product": best_match['product_name'],
            "quantity": best_match['quantity']
        }
        
    except Exception as e:
        print(f"Error adding {best_match['product_name']} to cart: {str(e)}")
        await page.close()
        return {
            "success": False,
            "product": best_match['product_name'],
            "error": str(e)
        }

async def parallel_add_to_cart(context, best_matches):
    """
    Add all best matches to cart in parallel using multiple tabs
    """
    print(f"Adding {len(best_matches)} items to cart in parallel...")
    
    # Create tasks for parallel execution
    tasks = [add_product_to_cart_in_tab(context, match) for match in best_matches]
    
    # Run all additions in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    success_count = 0
    for result in results:
        if isinstance(result, dict) and result.get("success"):
            success_count += 1
        else:
            print(f"Failed to add item: {result}")
    
    return {
        "total_items": len(best_matches),
        "successful_additions": success_count,
        "results": results
    }



async def shopping_flow(username, password, items=None):
    """
    Complete flow: search first, then login and add to cart
    """
    try:
        # Step 1: Parallel search using ONE browser with multiple tabs
        search_terms = ["מלפפון חצי קילו", "ביסלי בצל"]

        print("Starting parallel searches with single browser...")
        candidate_lists = await parallel_search_with_tabs(search_terms)
        
        # Step 1.5: Use LLM to find best matches from candidates
        best_matches = await find_best_matches_with_llm(candidate_lists)
        print(f"\n=== LLM Best Matches ===")
        for match in best_matches:
            print(f"User item: {match['user_item']}")
            print(f"Best match: {match['product_name']} ({match['product_code']}) - Quantity: {match['quantity']}")
            print(f"Reason: {match.get('reason', 'N/A')}")
            print()

        # Step 2: Login and add all best matches to cart in parallel
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()

            print("\nLogging in for cart operations...")
            await login_to_shufersal(page, username, password)
            print("✅ Login successful")
            
            # Close login page, context will maintain session
            await page.close()

            print("\nAdding best matches to cart sequentially...")
            cart_results = []
            for match in best_matches:
                print(f"Adding {match['product_name']} (quantity: {match['quantity']})...")
                result = await add_product_to_cart_in_tab(context, match)
                cart_results.append(result)
            
            # Count successes
            success_count = sum(1 for r in cart_results if r.get("success"))
            cart_summary = {
                "total_items": len(best_matches),
                "successful_additions": success_count,
                "results": cart_results
            }
            
            print(f"\n=== Cart Results ===")
            print(f"Successfully added {success_count}/{len(best_matches)} items to cart")

            await browser.close()

        return {
            "success": True,
            "message": "Successfully completed search-first flow"
        }

    except Exception as e:
        print(f"❌ Error: {str(e)}")
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
