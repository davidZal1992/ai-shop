"""
Test script for the enhanced add-to-cart functionality
Tests the new smart quantity handling with +/- buttons
"""
import requests
import json
import time
import sys
from loguru import logger

# Configure loguru to show debug messages
logger.add(sys.stderr, level="INFO")

CRAWLER_SERVER_URL = "http://localhost:8000"

def test_add_to_cart_with_quantity(product_name: str, quantity: float, product_code: str = ""):
    """Test adding a product to cart with specific quantity"""
    logger.info(f"🛒 Testing add to cart: {product_name} x{quantity}")
    
    try:
        response = requests.post(
            f"{CRAWLER_SERVER_URL}/add-to-cart",
            json={
                "product_name": product_name,
                "quantity": quantity,
                "product_code": product_code or f"TEST_{int(time.time())}"
            },
            timeout=120  # Increased timeout for complex operations
        )

        if response.status_code == 200:
            result = response.json()
            if result["success"]:
                logger.info(f"✅ Successfully added to cart: {result['message']}")
                return True
            else:
                logger.error(f"❌ Failed to add to cart: {result.get('error', 'Unknown error')}")
                return False
        else:
            logger.error(f"❌ HTTP Error: {response.status_code} - {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        logger.error("❌ Connection error: Is the crawler server running on http://localhost:8000?")
        return False
    except Exception as e:
        logger.error(f"❌ An unexpected error occurred: {e}")
        return False

def test_quantity_scenarios():
    """Test various quantity scenarios"""
    logger.info("🧪 Testing Enhanced Add to Cart Functionality")
    
    test_scenarios = [
        {
            "name": "Half Kilo Weight Product",
            "product_name": "מלפפון",
            "quantity": 0.5,
            "description": "Test 0.5 kg (half kilo) using +/- buttons"
        },
        {
            "name": "Quarter Kilo Weight Product", 
            "product_name": "עגבניות",
            "quantity": 0.25,
            "description": "Test 0.25 kg (quarter kilo) using +/- buttons"
        },
        {
            "name": "1.5 Kilo Weight Product",
            "product_name": "בצל",
            "quantity": 1.5, 
            "description": "Test 1.5 kg using +/- buttons"
        },
        {
            "name": "Unit-based Product",
            "product_name": "חלב",
            "quantity": 2,
            "description": "Test 2 units of milk"
        },
        {
            "name": "Single Unit Product",
            "product_name": "לחם",
            "quantity": 1,
            "description": "Test 1 unit of bread"
        }
    ]
    
    results = []
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n{'='*50}")
        print(f"🧪 Test {i}: {scenario['name']}")
        print(f"📝 Product: {scenario['product_name']}")
        print(f"🔢 Quantity: {scenario['quantity']}")
        print(f"📋 Description: {scenario['description']}")
        print("="*50)
        
        success = test_add_to_cart_with_quantity(
            scenario['product_name'],
            scenario['quantity']
        )
        
        results.append({
            'test': scenario['name'],
            'success': success
        })
        
        # Wait between tests to avoid overwhelming the server
        time.sleep(5)
    
    # Summary
    print(f"\n{'='*50}")
    print("📊 TEST RESULTS SUMMARY")
    print("="*50)
    
    passed = sum(1 for r in results if r['success'])
    total = len(results)
    
    for result in results:
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        print(f"{status} - {result['test']}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! Enhanced add-to-cart is working correctly.")
    else:
        logger.warning(f"⚠️ {total - passed} tests failed. Check the logs above for details.")

if __name__ == "__main__":
    print("🚀 Enhanced Add-to-Cart Test Suite")
    print("This will test the new smart quantity handling functionality.")
    print("Make sure the crawler server is running on http://localhost:8000")
    print()
    
    input("Press Enter to start the tests...")
    test_quantity_scenarios()
