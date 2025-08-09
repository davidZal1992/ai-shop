"""
Browser stability test script
Tests the browser lifecycle management and identifies potential issues
"""
import asyncio
import requests
import time
from loguru import logger
import sys

logger.add(sys.stderr, level="INFO")

CRAWLER_SERVER_URL = "http://localhost:8000"

async def test_browser_stability():
    """Test browser stability with multiple consecutive requests"""
    logger.info("🧪 Testing Browser Stability")
    
    test_searches = [
        "חלב",
        "מלפפון", 
        "לחם",
        "גבינה",
        "עגבניות"
    ]
    
    results = []
    
    for i, search_term in enumerate(test_searches, 1):
        logger.info(f"🔍 Test {i}/{len(test_searches)}: Searching for '{search_term}'")
        
        try:
            start_time = time.time()
            
            response = requests.post(
                f"{CRAWLER_SERVER_URL}/search",
                json={
                    "search_term": search_term,
                    "wait_time": 3,
                    "load_all_pages": False,
                    "max_scrolls": 2
                },
                timeout=60
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            if response.status_code == 200:
                result = response.json()
                if result["success"]:
                    logger.info(f"✅ Test {i} SUCCESS: Found {result['total_found']} products in {duration:.2f}s")
                    results.append({
                        'test': i,
                        'search_term': search_term,
                        'success': True,
                        'duration': duration,
                        'products_found': result['total_found']
                    })
                else:
                    logger.error(f"❌ Test {i} FAILED: {result.get('error', 'Unknown error')}")
                    results.append({
                        'test': i,
                        'search_term': search_term,
                        'success': False,
                        'error': result.get('error', 'Unknown error'),
                        'duration': duration
                    })
            else:
                logger.error(f"❌ Test {i} HTTP ERROR: {response.status_code}")
                results.append({
                    'test': i,
                    'search_term': search_term,
                    'success': False,
                    'error': f"HTTP {response.status_code}",
                    'duration': duration
                })
                
        except requests.exceptions.Timeout:
            logger.error(f"❌ Test {i} TIMEOUT after 60 seconds")
            results.append({
                'test': i,
                'search_term': search_term,
                'success': False,
                'error': 'Timeout',
                'duration': 60
            })
        except Exception as e:
            logger.error(f"❌ Test {i} EXCEPTION: {e}")
            results.append({
                'test': i,
                'search_term': search_term,
                'success': False,
                'error': str(e),
                'duration': 0
            })
        
        # Small delay between tests
        await asyncio.sleep(2)
    
    # Print summary
    print(f"\n{'='*60}")
    print("📊 BROWSER STABILITY TEST RESULTS")
    print("="*60)
    
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    print(f"✅ Successful tests: {len(successful)}/{len(results)}")
    print(f"❌ Failed tests: {len(failed)}/{len(results)}")
    
    if successful:
        avg_duration = sum(r['duration'] for r in successful) / len(successful)
        print(f"⏱️  Average successful duration: {avg_duration:.2f}s")
        
        total_products = sum(r.get('products_found', 0) for r in successful)
        print(f"🛒 Total products found: {total_products}")
    
    if failed:
        print(f"\n❌ Failed Tests:")
        for r in failed:
            print(f"  Test {r['test']} ({r['search_term']}): {r['error']}")
    
    # Health check
    try:
        health_response = requests.get(f"{CRAWLER_SERVER_URL}/health", timeout=10)
        if health_response.status_code == 200:
            health_data = health_response.json()
            print(f"\n🏥 Server Health: {health_data}")
        else:
            print(f"\n⚠️ Health check failed: {health_response.status_code}")
    except Exception as e:
        print(f"\n❌ Health check error: {e}")

def test_rapid_requests():
    """Test rapid consecutive requests to stress test browser"""
    logger.info("⚡ Testing Rapid Requests")
    
    for i in range(5):
        logger.info(f"🚀 Rapid request {i+1}/5")
        try:
            response = requests.post(
                f"{CRAWLER_SERVER_URL}/search",
                json={
                    "search_term": "test",
                    "wait_time": 1,
                    "load_all_pages": False,
                    "max_scrolls": 1
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                status = "✅ SUCCESS" if result["success"] else "❌ FAILED"
                logger.info(f"{status}: Rapid request {i+1}")
            else:
                logger.error(f"❌ HTTP {response.status_code}: Rapid request {i+1}")
                
        except Exception as e:
            logger.error(f"❌ Exception in rapid request {i+1}: {e}")
        
        # Very short delay
        time.sleep(0.5)

if __name__ == "__main__":
    print("🎯 Choose test to run:")
    print("1. Browser Stability Test (5 different searches)")
    print("2. Rapid Requests Test (stress test)")
    print("3. Both tests")
    
    choice = input("Enter choice (1-3): ").strip()
    
    if choice == "1":
        asyncio.run(test_browser_stability())
    elif choice == "2":
        test_rapid_requests()
    elif choice == "3":
        asyncio.run(test_browser_stability())
        test_rapid_requests()
    else:
        print("Invalid choice. Running stability test.")
        asyncio.run(test_browser_stability())
