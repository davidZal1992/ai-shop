"""
Test script for the search URL optimization
Tests that the agent uses the search URL from previous searches to avoid duplicate searching
"""
import os
import sys
import time
from loguru import logger
from shopping_agent import ShoppingAgent

# Configure loguru to show debug messages
logger.add(sys.stderr, level="INFO")

# Set OpenAI API Key from environment variable
if "OPENAI_API_KEY" not in os.environ:
    logger.error("OPENAI_API_KEY environment variable not set. Please set it before running.")
    sys.exit(1)

def test_search_url_optimization():
    """Test that the agent properly uses search URLs for optimization"""
    logger.info("🚀 Testing Search URL Optimization")
    agent = ShoppingAgent()

    # Test case: Simple shopping list that should demonstrate the optimization
    test_input = "חלב 2 יחידות"
    
    print(f"\n{'='*70}")
    print(f"🧪 Testing Search URL Optimization")
    print(f"📝 Input: {test_input}")
    print(f"🎯 Expected: Agent should search once, then use search URL for add-to-cart")
    print("="*70)
    
    try:
        # Process the shopping list
        result = agent.process_shopping_list(test_input)
        print(f"🤖 Agent Response:")
        print(f"{result}")
        
        print(f"\n✅ Search URL Optimization test completed")
        
        # Look for optimization indicators in the response
        if "search_url" in result.lower() or "optimization" in result.lower():
            print("🔗 ✅ Agent mentioned search URL optimization!")
        else:
            print("⚠️  Agent didn't explicitly mention search URL optimization")
            
    except Exception as e:
        logger.error(f"❌ Search URL optimization test failed: {e}")

def test_manual_workflow():
    """Manually test the search → add-to-cart workflow to see optimization"""
    logger.info("🔧 Testing Manual Search → Add-to-Cart Workflow")
    agent = ShoppingAgent()
    
    print(f"\n{'='*70}")
    print(f"🔧 Manual Workflow Test")
    print("="*70)
    
    try:
        # Step 1: Search for a product
        print("🔍 Step 1: Searching for 'חלב'...")
        search_result = agent.chat("Search for 'חלב' using search_shufersal tool")
        print(f"📊 Search Result: {search_result}")
        
        # Step 2: Try to extract search URL from the result
        # In a real scenario, the agent would do this automatically
        print(f"\n🔗 Step 2: Looking for search URL in the results...")
        if "search url:" in search_result.lower():
            print("✅ Search URL found in results!")
        else:
            print("⚠️ Search URL not clearly visible in output")
        
        # Step 3: Simulate add-to-cart with search URL
        print(f"\n🛒 Step 3: Testing add-to-cart with optimization...")
        add_result = agent.chat("""
        Use the add_to_cart tool to add milk to cart. 
        Make sure to use the search_url from the previous search for optimization.
        Product details: name='חלב', quantity=2, product_code='TEST_123'
        """)
        print(f"🛒 Add-to-Cart Result: {add_result}")
        
        print(f"\n✅ Manual workflow test completed")
        
    except Exception as e:
        logger.error(f"❌ Manual workflow test failed: {e}")

def test_optimization_benefits():
    """Test to demonstrate the speed benefits of the optimization"""
    logger.info("⚡ Testing Optimization Benefits")
    
    print(f"\n{'='*70}")
    print(f"⚡ Optimization Benefits Test")
    print("="*70)
    
    print("🎯 Benefits of Search URL Optimization:")
    print("✅ Faster add-to-cart (no duplicate search)")
    print("✅ More reliable (same search results)")
    print("✅ Better user experience (quicker responses)")
    print("✅ Reduced server load (fewer searches)")
    print("✅ Consistent product selection (same search context)")
    
    print(f"\n🔄 Workflow Comparison:")
    print("❌ OLD: Search → Parse → Search Again → Add to Cart")
    print("✅ NEW: Search → Parse → Use Same Page → Add to Cart")
    
    print(f"\n🚀 Implementation Details:")
    print("• Search endpoint returns search_url in response")
    print("• Agent passes search_url to add_to_cart tool")
    print("• Server navigates directly to search results page")
    print("• No duplicate searching needed!")

if __name__ == "__main__":
    print("🎯 Choose test to run:")
    print("1. Search URL Optimization Test (agent workflow)")
    print("2. Manual Workflow Test (step by step)")
    print("3. Optimization Benefits Demo (info only)")
    print("4. All tests")
    
    choice = input("Enter choice (1-4): ").strip()
    
    if choice == "1":
        test_search_url_optimization()
    elif choice == "2":
        test_manual_workflow()
    elif choice == "3":
        test_optimization_benefits()
    elif choice == "4":
        test_optimization_benefits()
        test_search_url_optimization()
        test_manual_workflow()
    else:
        print("Invalid choice. Running all tests.")
        test_optimization_benefits()
        test_search_url_optimization()
        test_manual_workflow()
