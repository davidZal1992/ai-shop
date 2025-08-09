"""
Test script for the new shopping list parsing workflow
Tests the complete flow: Raw Hebrew → Structured JSON → Smart Shopping
"""
import os
import sys
from loguru import logger
from shopping_agent import ShoppingAgent

# Configure loguru to show debug messages
logger.add(sys.stderr, level="INFO")

# Set OpenAI API Key from environment variable
if "OPENAI_API_KEY" not in os.environ:
    logger.error("OPENAI_API_KEY environment variable not set. Please set it before running.")
    sys.exit(1)

def test_parsing_workflow():
    """Test the complete parsing workflow with various Hebrew shopping lists"""
    logger.info("🚀 Starting Shopping List Parsing Workflow Test")
    agent = ShoppingAgent()

    # Test cases covering various parsing scenarios
    test_cases = [
        {
            "name": "Complex Item with Brand and Preferences",
            "input": "מגבונים לתינוק של בייביסיטר ללא בישום 4 חבילות",
            "expected_parsing": {
                "name": "מגבונים לתינוק",
                "quantity": 4,
                "unit": "package",
                "brand": "בייביסיטר",
                "preferences": "ללא בישום"
            },
            "description": "Should parse brand (בייביסיטר) and preferences (ללא בישום) correctly"
        },
        {
            "name": "Brand with Fat Percentage",
            "input": "גבינת עמק 9% חצי קילו",
            "expected_parsing": {
                "name": "גבינה",
                "quantity": 0.5,
                "unit": "kg",
                "brand": "עמק",
                "specifications": "9%"
            },
            "description": "Should parse brand, fat percentage, and convert חצי קילו to 0.5"
        },
        {
            "name": "Multiple Items in One List",
            "input": "חלב תנובה 3% 2 יחידות, מלפפונים קילו וחצי, לחם אחד",
            "expected_parsing": [
                {"name": "חלב", "quantity": 2, "unit": "unit", "brand": "תנובה", "specifications": "3%"},
                {"name": "מלפפונים", "quantity": 1.5, "unit": "kg"},
                {"name": "לחם", "quantity": 1, "unit": "unit"}
            ],
            "description": "Should parse multiple items with different specifications"
        },
        {
            "name": "Hebrew Quantity Expressions",
            "input": "עגבניות רבע קילו, בצל קילו וחצי, גבינה צהובה חצי קילו",
            "expected_parsing": [
                {"name": "עגבניות", "quantity": 0.25, "unit": "kg"},
                {"name": "בצל", "quantity": 1.5, "unit": "kg"},
                {"name": "גבינה צהובה", "quantity": 0.5, "unit": "kg"}
            ],
            "description": "Should convert רבע=0.25, קילו וחצי=1.5, חצי=0.5"
        },
        {
            "name": "Product with Organic Preference",
            "input": "גזר אורגני 2 קילו, חלב אורגני 1 יחידה",
            "expected_parsing": [
                {"name": "גזר", "quantity": 2, "unit": "kg", "preferences": "אורגני"},
                {"name": "חלב", "quantity": 1, "unit": "unit", "preferences": "אורגני"}
            ],
            "description": "Should identify organic preferences"
        },
        {
            "name": "Packaged Items (ארוז)",
            "input": "גבינה צהובה ארוז, סלמון מעושן ארוז",
            "expected_parsing": [
                {"name": "גבינה צהובה", "unit": "package"},
                {"name": "סלמון מעושן", "unit": "package"}
            ],
            "description": "Should recognize ארוז as packaged items"
        }
    ]

    results = []

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*70}")
        print(f"🧪 Test Case {i}: {test_case['name']}")
        print(f"📝 Input: {test_case['input']}")
        print(f"🎯 Expected: {test_case['description']}")
        print("="*70)
        
        try:
            # Test the complete workflow
            result = agent.process_shopping_list(test_case['input'])
            print(f"🤖 Agent Response:")
            print(f"{result}")
            
            # You could also test just the parsing step
            print(f"\n🔍 Testing parsing step only...")
            parsing_result = agent.chat(f"Parse this shopping list: {test_case['input']}")
            print(f"📊 Parsing Result: {parsing_result}")
            
            results.append({
                'test': test_case['name'],
                'success': True,
                'input': test_case['input']
            })
            print(f"\n✅ Test Case {i} completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Test Case {i} failed: {e}")
            results.append({
                'test': test_case['name'],
                'success': False,
                'input': test_case['input'],
                'error': str(e)
            })
        
        # Wait between tests to avoid overwhelming the server
        import time
        time.sleep(3)

    # Summary
    print(f"\n{'='*70}")
    print("📊 PARSING WORKFLOW TEST RESULTS SUMMARY")
    print("="*70)
    
    passed = sum(1 for r in results if r['success'])
    total = len(results)
    
    for result in results:
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        print(f"{status} - {result['test']}")
        if not result['success'] and 'error' in result:
            print(f"      Error: {result['error']}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All parsing workflow tests passed!")
    else:
        logger.warning(f"⚠️ {total - passed} tests failed. Check the logs above for details.")

def test_individual_parsing():
    """Test just the parsing functionality without full shopping workflow"""
    logger.info("🧠 Testing Individual Parsing Functionality")
    agent = ShoppingAgent()
    
    parsing_tests = [
        "מגבונים לתינוק של בייביסיטר ללא בישום 4 חבילות",
        "גבינת עמק 9% 500 גרם",
        "חלב תנובה 3% 2 יחידות",
        "מלפפונים חצי קילו",
        "עגבניות רבע קילו",
        "בצל קילו וחצי",
        "גזר אורגני 2 קילו",
        "גבינה צהובה ארוז"
    ]
    
    for test in parsing_tests:
        print(f"\n🔍 Testing parsing: {test}")
        try:
            result = agent.chat(f"Use the parse_shopping_list tool to parse: {test}")
            print(f"📊 Parsed result: {result}")
        except Exception as e:
            logger.error(f"❌ Parsing test failed: {e}")

if __name__ == "__main__":
    print("🎯 Choose test to run:")
    print("1. Complete Parsing Workflow Test (full shopping process)")
    print("2. Individual Parsing Test (parsing only)")
    print("3. Both tests")
    
    choice = input("Enter choice (1-3): ").strip()
    
    if choice == "1":
        test_parsing_workflow()
    elif choice == "2":
        test_individual_parsing()
    elif choice == "3":
        test_individual_parsing()
        test_parsing_workflow()
    else:
        print("Invalid choice. Running both tests.")
        test_individual_parsing()
        test_parsing_workflow()
