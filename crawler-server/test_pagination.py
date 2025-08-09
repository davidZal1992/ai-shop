"""
Test script to demonstrate infinite scroll/pagination functionality
"""
import requests
import json
from loguru import logger

def test_pagination():
    """Test the search with and without pagination"""
    
    search_term = "מלפפון"
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Shufersal Search with Pagination")
    print("=" * 60)
    
    # Test 1: Search without pagination (first page only)
    print(f"\n📄 Test 1: Search '{search_term}' - First page only")
    print("-" * 40)
    
    response1 = requests.post(f"{base_url}/search", json={
        "search_term": search_term,
        "wait_time": 3,
        "load_all_pages": False,  # Only first page
        "take_screenshot": False
    })
    
    if response1.status_code == 200:
        result1 = response1.json()
        if result1["success"]:
            print(f"✅ Found {len(result1['products'])} products (first page only)")
            for i, product in enumerate(result1['products'][:3], 1):
                print(f"  {i}. {product['name']} - ₪{product['price']}")
        else:
            print(f"❌ Error: {result1.get('error')}")
    else:
        print(f"❌ HTTP Error: {response1.status_code}")
    
    # Test 2: Search with pagination (all pages)
    print(f"\n📄 Test 2: Search '{search_term}' - All pages with infinite scroll")
    print("-" * 40)
    
    response2 = requests.post(f"{base_url}/search", json={
        "search_term": search_term,
        "wait_time": 3,
        "load_all_pages": True,   # Load all pages
        "max_scrolls": 5,         # Maximum 5 scrolls
        "take_screenshot": False
    })
    
    if response2.status_code == 200:
        result2 = response2.json()
        if result2["success"]:
            print(f"✅ Found {len(result2['products'])} products (all pages)")
            print(f"📊 Improvement: {len(result2['products']) - len(result1['products']) if result1.get('products') else 0} more products")
            
            # Show first few products
            for i, product in enumerate(result2['products'][:5], 1):
                print(f"  {i}. {product['name']} - ₪{product['price']}")
            
            if len(result2['products']) > 5:
                print(f"  ... and {len(result2['products']) - 5} more products")
                
            # Show cheapest products
            sorted_products = sorted(result2['products'], key=lambda x: x['price'])
            print(f"\n💰 Top 3 Cheapest:")
            for i, product in enumerate(sorted_products[:3], 1):
                print(f"  {i}. {product['name']} - ₪{product['price']}")
                
        else:
            print(f"❌ Error: {result2.get('error')}")
    else:
        print(f"❌ HTTP Error: {response2.status_code}")
    
    print(f"\n✅ Pagination test completed!")

if __name__ == "__main__":
    test_pagination()
