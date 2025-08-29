import asyncio
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import openai
import os
from dotenv import load_dotenv
from shufersal_crawler_service import shopping_flow
from playwright.async_api import async_playwright

load_dotenv()

app = FastAPI()

class ShoppingItem(BaseModel):
    product_name: str
    brand: Optional[str] = None
    quantity: float
    unit: str  # "kg", "grams", "pieces", "liters", etc.
    preferences: Optional[str] = None  # e.g., "טעם וניל", "אורגני", "דל שומן"

class ShoppingRequest(BaseModel):
    items_text: str

class ShoppingResponse(BaseModel):
    items: List[ShoppingItem]

class ShopRequest(BaseModel):
    items_text: str
    username: str
    password: str

class ShopResponse(BaseModel):
    parsed_items: List[ShoppingItem]
    success: bool
    message: str

# Configure OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

SHOPPING_PARSER_PROMPT = """
You are a shopping expert AI that parses Hebrew shopping requests into structured JSON.

Your task is to parse shopping requests in Hebrew and return a JSON list of products.

For each product, extract:
- product_name: The main product (e.g., "מעדן חלבון", "מלפפון", "חלב")
- brand: Brand name if mentioned (e.g., "גו", "תנובה", "שטראוס")
- quantity: Numeric quantity (e.g., 8, 2.5, 1)
- unit: Unit of measurement:
  - "pieces" for countable items (8 יחידות, 3 קופסאות)
  - "kg" for kilograms 
  - "grams" for grams
  - "liters" for liters
  - "ml" for milliliters
  - if nothing provided use pieces as default, and if number is not provided use 1 as default
- preferences: Any taste, flavor, or specific requirements (e.g., "טעם וניל", "אורגני", "דל שומן")

Examples:
Input: "מעדן חלבון גו טעם וניל 8 כאלה"
Output: [{"product_name": "מעדן חלבון", "brand": "גו", "quantity": 8, "unit": "pieces", "preferences": "טעם וניל"}]

Input: "מלפפון 2 קילו וגם חלב תנובה 3 ליטר 1%"
Output: [
  {"product_name": "מלפפון", "brand": null, "quantity": 2, "unit": "kg", "preferences": null},
  {"product_name": "חלב", "brand": "תנובה", "quantity": 3, "unit": "liters", "preferences": 1%}
]

Input: "עגבניות 500 גרם אורגני ולחם שחור 2 כיכרות"
Output: [
  {"product_name": "עגבניות", "brand": null, "quantity": 500, "unit": "grams", "preferences": "אורגני"},
  {"product_name": "לחם שחור", "brand": null, "quantity": 2, "unit": "pieces", "preferences": null}
]

Return ONLY valid JSON array, no other text.
"""

async def parse_shopping_list(items_text: str) -> List[ShoppingItem]:
    """
    Use OpenAI to parse shopping list text into structured items
    """
    try:
        client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": SHOPPING_PARSER_PROMPT},
                {"role": "user", "content": items_text}
            ],
            temperature=0.1
        )
        
        parsed_json = json.loads(response.choices[0].message.content)
        return [ShoppingItem(**item) for item in parsed_json]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse shopping list: {str(e)}")


async def shop_with_parsed_items(username, password, items: List[ShoppingItem]):
    """
    Execute shopping automation with parsed items using the service
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            # Login using the service
            await login_to_shufersal(page, username, password)
            print("✅ Login successful")
            
            # Process each item
            for item in items:
                print(f"Processing: {item.quantity} {item.unit} {item.product_name}")
                
                # Search for product using the service
                search_term = f"{item.brand} {item.product_name}" if item.brand else item.product_name
                await search_product(page, search_term)
                print(f"✅ Searched for {search_term}")
                
                # Add to cart with quantity
                try:
                    # Set quantity first
                    await page.fill("input.js-qty-selector-input", str(item.quantity))
                    
                    # Click add button
                    try:
                        await page.click('button:has-text("הוספה")', timeout=5000)
                    except:
                        await page.click('.js-add-to-cart', timeout=5000)
                    
                    await page.wait_for_timeout(2000)
                    print(f"✅ Added {item.quantity} {item.unit} to cart")
                except Exception as e:
                    print(f"⚠️ Could not add to cart: {str(e)}")
            
            await browser.close()
            return {
                "success": True,
                "message": f"Successfully processed {len(items)} items"
            }
            
        except Exception as e:
            await browser.close()
            return {
                "success": False,
                "message": f"Error: {str(e)}"
            }

@app.post("/shop")
async def shop_endpoint(request: ShopRequest):
    """
    Parse shopping list and execute Shufersal automation
    """
    # Parse the shopping list
    # items = await parse_shopping_list(request.items_text)
    
    # Execute the complete shopping flow using the service
    result = await shopping_flow(request.username, request.password, None)
    
    return {
        # "parsed_items": [item.model_dump() for item in items],
        "success": result["success"],
        "message": result["message"]
    }

@app.get("/")
async def root():
    return {"message": "Shopping List Parser API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)