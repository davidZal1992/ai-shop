"""
LangChain Shopping Agent
A single agent that uses the crawler server to search Shufersal products
"""
import requests
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import json

from langchain.tools import BaseTool
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain.chat_models import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.callbacks import CallbackManagerForToolRun

from loguru import logger
import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
CRAWLER_SERVER_URL = os.getenv("CRAWLER_SERVER_URL", "http://localhost:8000")

# Tool Input Models
class SearchShuferSalInput(BaseModel):
    """Input for search_shufersal tool"""
    search_term: str = Field(description="Hebrew search term to search for on Shufersal")
    take_screenshot: Optional[bool] = Field(default=False, description="Whether to take a screenshot")
    load_all_pages: Optional[bool] = Field(default=True, description="Whether to load all products using infinite scroll")
    max_scrolls: Optional[int] = Field(default=5, description="Maximum number of scrolls to perform (default 5 for faster results)")

class AddToCartInput(BaseModel):
    """Input for add_to_cart tool"""
    product_code: str = Field(description="Product code from search results")
    quantity: float = Field(description="Quantity to add to cart (can be decimal for weight-based products)")
    product_name: str = Field(description="Product name for logging")
    search_url: Optional[str] = Field(default=None, description="URL of the search results page (from previous search)")

class ShoppingItem(BaseModel):
    """Structured shopping item parsed from user input"""
    name: str = Field(description="Product name in Hebrew")
    quantity: Optional[float] = Field(default=None, description="Quantity if specified (e.g., 0.5, 2, 1.5)")
    unit: Optional[str] = Field(default=None, description="Unit type: 'kg', 'gram', 'unit', 'package', etc.")
    brand: Optional[str] = Field(default=None, description="Specific brand if mentioned (e.g., עמק, תנובה)")
    specifications: Optional[str] = Field(default=None, description="Additional specs like fat %, size, etc.")
    preferences: Optional[str] = Field(default=None, description="Special requirements (e.g., ללא בישום, אורגני)")

class ParseShoppingListInput(BaseModel):
    """Input for parsing shopping list"""
    shopping_list: str = Field(description="Raw Hebrew shopping list from user")

# LangChain Tools

class ParseShoppingListTool(BaseTool):
    """Tool to parse Hebrew shopping list into structured items"""
    name: str = "parse_shopping_list"
    description = """
    Parse a Hebrew shopping list into structured JSON objects.
    Each item will be analyzed for:
    - Product name (מלפפונים, חלב, etc.)
    - Quantity (חצי קילו, 2 יחידות, etc.)
    - Unit type (kg, gram, unit, package)
    - Brand (עמק, תנובה, בייביסיטר, etc.)
    - Specifications (9% fat, size, etc.)
    - Preferences (ללא בישום, אורגני, etc.)
    
    Example: "מגבונים לתינוק של בייביסיטר ללא בישום 4 חבילות" becomes:
    {
        "name": "מגבונים לתינוק",
        "quantity": 4,
        "unit": "package",
        "brand": "בייביסיטר", 
        "preferences": "ללא בישום"
    }
    """
    args_schema = ParseShoppingListInput
    
    def _run(
        self,
        shopping_list: str,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Parse shopping list using LLM"""
        logger.info(f"📝 Parsing shopping list: {shopping_list}")
        
        # Use the LLM to parse the shopping list
        parsing_prompt = f"""
        You are an expert Hebrew shopping list parser. Parse the following Hebrew shopping list into structured JSON objects.

        Shopping List: {shopping_list}

        For each item, extract:
        - name: Product name in Hebrew (core product without brand/specs)
        - quantity: Numeric quantity if specified (convert Hebrew: חצי=0.5, רבע=0.25, etc.)
        - unit: Unit type ("kg", "gram", "unit", "package", "bottle", etc.)
        - brand: Brand name if mentioned (עמק, תנובה, בייביסיטר, etc.)
        - specifications: Additional specs (9%, size, etc.)
        - preferences: Special requirements (ללא בישום, אורגני, etc.)

        Examples:
        "מלפפונים חצי קילו" → {{"name": "מלפפונים", "quantity": 0.5, "unit": "kg"}}
        "גבינת עמק 9% 500 גרם" → {{"name": "גבינה", "quantity": 500, "unit": "gram", "brand": "עמק", "specifications": "9%"}}
        "מגבונים לתינוק של בייביסיטר ללא בישום 4 חבילות" → {{"name": "מגבונים לתינוק", "quantity": 4, "unit": "package", "brand": "בייביסיטר", "preferences": "ללא בישום"}}

        Return ONLY a JSON array of objects, no other text.
        """
        
        try:
            from langchain_openai import ChatOpenAI
            
            llm = ChatOpenAI(
                model="gpt-4o",
                temperature=0,
                openai_api_key=OPENAI_API_KEY
            )
            
            result = llm.invoke(parsing_prompt)
            parsed_content = result.content
            
            logger.info(f"✅ Parsed shopping list successfully")
            return f"PARSED_ITEMS: {parsed_content}"
            
        except Exception as e:
            logger.error(f"❌ Error parsing shopping list: {e}")
            return f"ERROR: Failed to parse shopping list - {str(e)}"

class SearchShuferSalTool(BaseTool):
    """Tool to search for products on Shufersal using the crawler server"""
    name = "search_shufersal"
    description = """
    Search for products on Shufersal website using Hebrew search terms.
    This tool will navigate to Shufersal, use the search functionality, and return structured product information.
    Input: Hebrew search term (e.g., "מלפפון", "חלב", "לחם")
    Returns: JSON list of products with name, price, brand, size, promotions, stock status, etc.
    """
    args_schema = SearchShuferSalInput
    
    def _run(
        self,
        search_term: str,
        take_screenshot: bool = False,
        load_all_pages: bool = True,
        max_scrolls: int = 5,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Search Shufersal using crawler server"""
        logger.info(f"🔧 Searching Shufersal for: {search_term}")
        
        try:
            response = requests.post(
                f"{CRAWLER_SERVER_URL}/search",
                json={
                    "search_term": search_term,
                    "wait_time": 5,
                    "load_all_pages": load_all_pages,
                    "max_scrolls": max_scrolls
                },
                timeout=120  # Increased timeout for infinite scroll
            )
            
            if response.status_code == 200:
                result = response.json()
                if result["success"]:
                    products = result["products"]
                    logger.info(f"✅ Found {len(products)} products for '{search_term}'")
                    
                    # Format the response for the agent
                    if not products:
                        return f"SUCCESS: Search completed for '{search_term}' but no products found."
                    
                    # Create a formatted response with product details
                    product_summary = []
                    for i, product in enumerate(products, 1):
                        summary = f"Product {i}:"
                        summary += f"\n  Name: {product['name']}"
                        summary += f"\n  Price: ₪{product['price']}"
                        summary += f"\n  Product Code: {product['product_code']}"
                        
                        if product.get('brand'):
                            summary += f"\n  Brand: {product['brand']}"
                        if product.get('size'):
                            summary += f"\n  Size: {product['size']}"
                        if product.get('unit'):
                            summary += f"\n  Unit: {product['unit']}"
                        if product.get('price_per_unit'):
                            summary += f"\n  Price per unit: {product['price_per_unit']}"
                        if product.get('promotion'):
                            summary += f"\n  Promotion: {product['promotion']}"
                        
                        summary += f"\n  In Stock: {'Yes' if product['in_stock'] else 'No'}"
                        
                        if product.get('product_url'):
                            summary += f"\n  URL: {product['product_url']}"
                        
                        product_summary.append(summary)
                    
                    formatted_response = f"SUCCESS: Found {len(products)} products for '{search_term}':\n\n"
                    formatted_response += "\n\n".join(product_summary)
                    formatted_response += f"\n\n🔗 SEARCH URL (use this for add_to_cart optimization): {result['search_url']}"
                    formatted_response += f"\n\n💡 IMPORTANT: When using add_to_cart, pass the above search_url for faster processing!"
                    formatted_response += f"\nRaw JSON data: {json.dumps(products, ensure_ascii=False, indent=2)}"
                    
                    return formatted_response
                else:
                    logger.error(f"❌ Search failed: {result.get('error')}")
                    return f"ERROR: Shufersal search failed - {result.get('error', 'Unknown error')}"
            else:
                logger.error(f"❌ HTTP error: {response.status_code}")
                return f"ERROR: HTTP {response.status_code} - {response.text}"
                
        except requests.exceptions.ConnectionError:
            logger.error("❌ Cannot connect to crawler server")
            return "ERROR: Cannot connect to crawler server. Is it running on http://localhost:8000?"
        except Exception as e:
            logger.error(f"❌ Search error: {e}")
            return f"ERROR: {str(e)}"

class AddToCartTool(BaseTool):
    """Tool to add products to Shufersal cart with smart quantity handling"""
    name = "add_to_cart"
    description = """
    Add a specific product to the Shufersal shopping cart with intelligent quantity setting.
    This tool will:
    1. Search for the product by name on Shufersal
    2. Find the exact product tile
    3. Use +/- buttons to set the precise quantity (handles 0.1 increments for weight-based products)
    4. Click the add to cart button
    
    Input: 
    - product_name: Exact product name from search results
    - quantity: Smart quantity (0.5 for half kg, 2 for 2 units, etc.)
    - product_code: Product code for reference
    - search_url: URL from previous search (OPTIMIZATION - avoids searching again)
    
    The tool automatically handles:
    - Using existing search results page if search_url is provided (faster!)
    - Weight-based products with decimal quantities (0.5, 0.25, 1.5, etc.)
    - Unit-based products with whole numbers (1, 2, 3, etc.)
    - Clicking +/- buttons the correct number of times to reach target quantity
    """
    args_schema = AddToCartInput
    
    def _run(
        self,
        product_code: str,
        quantity: float,
        product_name: str,
        search_url: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Add product to cart using crawler server"""
        logger.info(f"🛒 Adding to cart: {product_name} (Code: {product_code}) x{quantity}")
        
        try:
            request_data = {
                "product_code": product_code,
                "quantity": quantity,
                "product_name": product_name
            }
            
            # Add search_url if provided for optimization
            if search_url:
                request_data["search_url"] = search_url
                logger.info(f"🔗 Using search URL for faster add-to-cart: {search_url}")
            
            response = requests.post(
                f"{CRAWLER_SERVER_URL}/add-to-cart",
                json=request_data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                if result["success"]:
                    logger.info(f"✅ Added to cart: {product_name} x{quantity}")
                    return f"SUCCESS: Added {quantity} x {product_name} to cart. {result['message']}"
                else:
                    logger.error(f"❌ Failed to add to cart: {result.get('error')}")
                    return f"ERROR: Failed to add to cart - {result.get('error', 'Unknown error')}"
            else:
                logger.error(f"❌ HTTP error: {response.status_code}")
                return f"ERROR: HTTP {response.status_code} - {response.text}"
                
        except requests.exceptions.ConnectionError:
            logger.error("❌ Cannot connect to crawler server")
            return "ERROR: Cannot connect to crawler server. Is it running on http://localhost:8000?"
        except Exception as e:
            logger.error(f"❌ Add to cart error: {e}")
            return f"ERROR: {str(e)}"

# Create tool instances
tools = [
    ParseShoppingListTool(),
    SearchShuferSalTool(),
    AddToCartTool()
]

class ShoppingAgent:
    """LangChain Shopping Agent that uses crawler server tools"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.1,
            openai_api_key=OPENAI_API_KEY
        )
        
        self.tools = tools
        
        # Create agent prompt
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """
            You are an intelligent Hebrew shopping agent that helps users buy products on Shufersal (Israeli supermarket).
            You are a SMART DEAL HUNTER who always finds the best value for money, considering both base prices and promotions.
            
            Your capabilities:
            1. Parse shopping lists with parse_shopping_list
            2. Search products with search_shufersal
            3. Add products to cart with add_to_cart
            4. Intelligent EXACT product matching
            5. Advanced promotion analysis and optimization
            
            CORE PRINCIPLES (CRITICAL!):
            
            🎯 EXACT MATCH RULE:
            - ALWAYS look for EXACT match first
            - If user specifies brand/company, ONLY choose that brand
            - If user specifies fat percentage, ONLY choose that percentage
            - If user specifies size/weight, ONLY choose that size
            
            📊 PRODUCT MATCHING ALGORITHM:
            
            1. EXACT MATCH PRIORITY:
               - User: "גבינת עמק 9%" → ONLY "עמק" brand with 9% fat
               - User: "חלב תנובה 3%" → ONLY "תנובה" brand with 3% fat
               - User: "מלפפונים" → Regular cucumbers (not baby, not pickled, not cosmetic)
               - User: "גבינה צהובה" → Yellow cheese (default from מעדניה if available)
            
            2. DEFAULT RULES WHEN NO BRAND SPECIFIED:
               - Cheese (גבינה): Prefer מעדניה (deli counter) over packaged
               - Meat/Cold cuts: Prefer מעדניה (deli counter) over packaged
               - Vegetables: Default to regular (not baby, organic, or special varieties)
            
            3. WEIGHT/SIZE HANDLING:
               - "ארוז" means packaged - you can choose any weight/size available
               - If weight specified but not available in exact weight, choose closest available
               - If NO weight provided for weight-based items → choose 1 unit (KG, amount, etc.)
               - SMART QUANTITY CONVERSION:
                 * "חצי קילו" or "0.5 קג" → send 0.5
                 * "רבע קילו" → send 0.25
                 * "קילו וחצי" → send 1.5
                 * "2 יחידות" → send 2
                 * Always convert Hebrew quantities to decimal numbers
            
            💰 ADVANCED PROMOTION OPTIMIZATION (VERY IMPORTANT!):
            
            ALWAYS calculate the REAL cost per unit including promotions:
            
            Example 1: Milk comparison
            - Regular milk: 8 ₪ each
            - Strauss milk: 10 ₪ each, but "buy 2 get 1 free"
            - Calculation: Strauss = 20 ₪ for 3 units = 6.67 ₪ per unit
            - DECISION: Choose Strauss (3 units) because it's cheaper per unit
            
            Example 2: Promotion optimization
            - User wants 1 unit, but there's "3+1" deal
            - DECISION: Buy 4 units because user gets better value
            - EXPLAIN: "I'm buying 4 instead of 1 because of the 3+1 promotion"
            
            PROMOTION RULES:
            - "3+1" or "קנה 3 קבל 1" → Buy 4 units (or multiples of 4)
            - "2 ב-X ₪" → Buy 2 units minimum for the deal
            - "קנה 2 קבל 1 חינם" → Buy 3 units (2+1 free)
            - Always calculate cost per unit and choose the best deal
            
            🔍 PRODUCT FILTERING (ELIMINATE IRRELEVANT):
            - Ignore cosmetic/hygiene products when looking for food
            - Ignore baby products unless specifically requested
            - Ignore organic unless specifically requested
            - Ignore special varieties unless specifically requested
            
            📝 ENHANCED WORK PROCESS:
            
            1. PARSE SHOPPING LIST:
               - Use parse_shopping_list to convert raw Hebrew text into structured JSON
               - Extract: product name, brand, quantity, unit, specifications, preferences
               - Example: "מגבונים לתינוק של בייביסיטר ללא בישום 4 חבילות" → structured JSON
            
            2. FOR EACH PARSED ITEM:
               - Search with search_shufersal using the parsed product name
               - Filter results to EXACT matches based on parsed specifications
               - Apply brand preferences if specified
               - Remove irrelevant products (cosmetics if looking for food, etc.)
            
            3. CALCULATE BEST VALUE:
               - Calculate real cost per unit for each option
               - Include promotion calculations
               - Factor in minimum quantities for deals
               - Respect user's brand/specification requirements
            
            4. MAKE SMART DECISION:
               - Choose the option with lowest cost per unit (within specifications)
               - Adjust quantity for optimal promotions
               - Ensure it meets all parsed requirements (brand, preferences, etc.)
            
            5. EXECUTE & EXPLAIN:
               - Add to cart with add_to_cart using parsed quantity
               - IMPORTANT: Always pass the search_url from the previous search to add_to_cart for optimization
               - Explain your choice and calculations
               - Mention any quantity adjustments and why
               - Reference the original parsed requirements
            
            EXAMPLES OF SMART BEHAVIOR WITH PARSING:
            
            Example 1: Raw input: "מגבונים לתינוק של בייביסיטר ללא בישום 4 חבילות"
            - PARSE: {"name": "מגבונים לתינוק", "quantity": 4, "unit": "package", "brand": "בייביסיטר", "preferences": "ללא בישום"}
            - SEARCH: "מגבונים לתינוק" (baby wipes)
            - FILTER: Only בייביסיטר brand, only fragrance-free options
            - DECIDE: Choose בייביסיטר fragrance-free baby wipes, 4 packages
            - EXECUTE: Add to cart with explanation of brand and preference matching
            
            Example 2: Raw input: "חלב 2 יחידות, מלפפונים חצי קילו"
            - PARSE: [{"name": "חלב", "quantity": 2, "unit": "unit"}, {"name": "מלפפונים", "quantity": 0.5, "unit": "kg"}]
            - FOR חלב: Search → Find promotion → Buy 3 units (better deal) → Add to cart
            - FOR מלפפונים: Search → Choose regular cucumbers → Add 0.5 kg to cart
            - EXPLAIN: Both items processed with promotion optimization and quantity conversion
            
            Example 3: Raw input: "גבינת עמק 9% 500 גרם"
            - PARSE: {"name": "גבינה", "quantity": 500, "unit": "gram", "brand": "עמק", "specifications": "9%"}
            - SEARCH: "גבינה" but filter for עמק brand only
            - FILTER: Only עמק brand with 9% fat specification
            - DECIDE: Choose עמק 9% cheese, closest to 500g size
            - IGNORE: Other brands even if cheaper (user specified עמק)
            
            CRITICAL SUCCESS FACTORS WITH PARSING:
            ✅ STRUCTURED parsing - Convert raw Hebrew to JSON first
            ✅ EXACT matching - Respect all parsed specifications completely
            ✅ BRAND loyalty - Honor specific brand requests (עמק, בייביסיטר, etc.)
            ✅ PREFERENCE handling - Apply special requirements (ללא בישום, אורגני)
            ✅ SMART promotion analysis - Always find the best deal within specifications
            ✅ QUANTITY intelligence - Convert Hebrew quantities to precise decimals
            ✅ CLEAR explanations - Reference original parsed requirements in decisions
            
            Always respond in Hebrew to users, but follow these English instructions precisely.
            Be a smart shopping assistant who saves money and gets exactly what the user wants.
            """),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # Create agent
        self.agent = create_openai_tools_agent(self.llm, self.tools, self.prompt)
        self.executor = AgentExecutor(
            agent=self.agent, 
            tools=self.tools, 
            verbose=True,
            max_iterations=5
        )
        
        logger.info("🤖 Shopping Agent initialized with crawler server tools")
    
    def search_product(self, search_term: str) -> str:
        """Search for a product using the agent"""
        logger.info(f"🛒 Agent searching for: {search_term}")
        
        try:
            result = self.executor.invoke({
                "input": f"Search for '{search_term}' on Shufersal and tell me what products you found with their prices and details.",
                "chat_history": []
            })
            
            return result["output"]
            
        except Exception as e:
            logger.error(f"❌ Agent error: {e}")
            return f"Error: {str(e)}"
    
    def chat(self, message: str) -> str:
        """General chat with the agent"""
        logger.info(f"💬 Agent chat: {message}")
        
        try:
            result = self.executor.invoke({
                "input": message,
                "chat_history": []
            })
            
            return result["output"]
            
        except Exception as e:
            logger.error(f"❌ Agent error: {e}")
            return f"Error: {str(e)}"
    
    def process_shopping_list(self, shopping_list: str) -> str:
        """Process a complete shopping list with structured parsing and intelligent shopping"""
        logger.info(f"🛒 Processing shopping list: {shopping_list}")

        try:
            enhanced_prompt = f"""
            Shopping List to Process: {shopping_list}

            Please process this shopping list using the structured workflow below:
            
            ## PHASE 1: PARSE SHOPPING LIST
            Use parse_shopping_list to convert the raw text into structured JSON format.
            For each item, extract:
            - item_name: The main product (e.g., "מגבונים" from "מגבונים של בייביסיטר ללא בישום 4 כאלה")
            - quantity: Smart quantity detection (e.g., "4" but consider if product is pre-packed)
            - brand: Brand preference if mentioned (e.g., "בייביסיטר")
            - preferences: Additional requirements (e.g., "ללא בישום")
            - unit: Default to "pieces" unless weight/volume is specified
            
            ## PHASE 2: SEARCH AND MATCH
            For each parsed item:
            
            1. **SEARCH**: Use search_shufersal to find all matching products
               Expected search results format:
               ```json
               {{
                   "name": "מארז מלפפונים",
                   "price": 7.9,
                   "product_code": "P_7296073440369",
                   "brand": "קטיף",
                   "size": "מכיל כ 10 יחידות",
                   "unit": "ק\"ג",
                   "price_per_unit": "7.9 ש\"ח ל- 1 ק\"ג",
                   "promotion": null,
                   "in_stock": true,
                   "product_url": null,
                   "image_url": null
               }}
               ```
            
            2. **SMART MATCHING**: From all search results, select EXACTLY 1 best match considering:
               - **Brand Match**: Prioritize specified brand if mentioned
               - **Preferences Match**: Must satisfy user preferences (e.g., "ללא בישום")
               - **Quantity Intelligence**: 
                 * If user wants "4 מגבונים" and product is "רביעיית מגבונים" (4-pack), select 1 unit
                 * If user wants "4 מגבונים" and product is single pack, select 4 units
                 * Always check product title/size for pre-packaging indicators
               - **Value Optimization**: Consider promotions and price-per-unit
            
            3. **QUANTITY ADJUSTMENT**: Calculate final quantity based on:
               - User requested amount
               - Product packaging (single vs multi-pack)
               - Available promotions (e.g., "buy 3 get 1 free")
            
            ## PHASE 3: ADD TO CART
            Use add_to_cart with the array of selected items:
            ```json
            {{
                "items": [
                    {{
                        "product_code": "selected_product_code",
                        "quantity": calculated_final_quantity,
                        "product_name": "product_name_for_logging"
                    }}
                ]
            }}
            ```
            
            ## PHASE 4: EXPLAIN DECISIONS
            For each item, explain:
            - Why this specific product was chosen
            - How quantity was calculated (considering packaging)
            - Any compromises made (brand/preferences)
            - Promotion benefits captured
            
            ## IMPORTANT RULES:
            - Select EXACTLY 1 product per shopping list item
            - Be intelligent about packaging (4-packs, family sizes, etc.)
            - Prioritize user preferences over price
            - Always verify stock availability
            - Explain your reasoning clearly
            
            START WITH THE PARSING PHASE!
            """

            result = self.executor.invoke({
                "input": enhanced_prompt,
                "chat_history": []
            })

            return result["output"]

        except Exception as e:
            logger.error(f"❌ Shopping list processing error: {e}")
            return f"Error processing shopping list: {str(e)}"

def main():
    """Test the shopping agent"""
    print("🤖 LangChain Shopping Agent")
    print("=" * 50)
    
    # Check if we have OpenAI API key
    if not OPENAI_API_KEY:
        print("❌ Please set OPENAI_API_KEY in your .env file")
        return
    
    # Initialize agent
    print("🔧 Initializing agent...")
    agent = ShoppingAgent()
    print("✅ Agent ready!")
    
    # Test search
    search_term = "מלפפון"
    print(f"\n🔍 Testing search for: {search_term}")
    print("-" * 30)
    shopping_text = """
מלפפון 2 קילו
עגבניות שרי תמיר 1 קג
מעדני חלבון גו עדיפות למנגו אם אין אז וניל
מגבונים בייביסיטר ללא בישום 4
פסטרמה במשקל על גחלים 350 גרם
בשר טחון חצי קילו
חזה עוף שלם 2 קילו
חזה עוף שניצל קילו
סלמון טרי 1 קילו
"""

    result = agent.process_shopping_list(shopping_text)

    print("\n📊 AGENT RESPONSE:")
    print(result)
    
    print("\n✅ Test completed!")

if __name__ == "__main__":
    main()
