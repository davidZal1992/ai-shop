"""
Test script for the enhanced smart shopping agent
Tests intelligent product matching, quantity conversion, and promotion optimization
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

def test_enhanced_smart_agent():
    logger.info("🚀 Starting Enhanced Smart Shopping Agent Test")
    agent = ShoppingAgent()

    # Test cases covering the new enhanced functionality
    test_cases = [
        {
            "name": "Smart Quantity Conversion - Half Kilo",
            "input": "מלפפונים חצי קילו",
            "expected": "Should convert 'חצי קילו' to 0.5 and choose regular cucumbers"
        },
        {
            "name": "Exact Brand Match with Fat Percentage", 
            "input": "גבינת עמק 9% 500 גרם",
            "expected": "Should ONLY choose עמק brand with 9% fat, ignore cheaper alternatives"
        },
        {
            "name": "Deli Preference for Cheese",
            "input": "גבינה צהובה רבע קילו", 
            "expected": "Should prefer מעדניה option, convert 'רבע קילו' to 0.25"
        },
        {
            "name": "Smart Promotion Optimization",
            "input": "חלב 2 יחידות",
            "expected": "Should find best promotion deal, possibly adjust quantity for better value"
        },
        {
            "name": "Complex Shopping List",
            "input": "מלפפונים קילו וחצי, חלב תנובה 3% 1 יחידה, גבינה צהובה ארוז חצי קילו",
            "expected": "Should handle multiple items with different quantity types and brand specifications"
        }
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"🧪 Test Case {i}: {test_case['name']}")
        print(f"📝 Input: {test_case['input']}")
        print(f"🎯 Expected: {test_case['expected']}")
        print("="*60)
        
        try:
            result = agent.process_shopping_list(test_case['input'])
            print(f"🤖 Agent Response:")
            print(f"{result}")
            print(f"\n✅ Test Case {i} completed")
        except Exception as e:
            logger.error(f"❌ Test Case {i} failed: {e}")
        
        # Wait between tests to avoid overwhelming the server
        import time
        time.sleep(3)

    logger.info("✅ Enhanced Smart Shopping Agent Test Completed")

def test_quantity_intelligence():
    """Test the agent's ability to understand Hebrew quantity expressions"""
    logger.info("🧠 Testing Quantity Intelligence")
    agent = ShoppingAgent()
    
    quantity_tests = [
        "חצי קילו עגבניות",  # Half kilo tomatoes
        "רבע קילו גבינה צהובה",  # Quarter kilo yellow cheese  
        "קילו וחצי בצל",  # 1.5 kg onions
        "2 יחידות חלב",  # 2 units milk
        "3 לחמניות",  # 3 bread rolls
    ]
    
    for test in quantity_tests:
        print(f"\n🔢 Testing quantity conversion: {test}")
        try:
            result = agent.chat(f"הסבר לי איך תמיר את הכמות ב: {test}")
            print(f"🤖 Agent explanation: {result}")
        except Exception as e:
            logger.error(f"❌ Quantity test failed: {e}")

if __name__ == "__main__":
    print("🎯 Choose test to run:")
    print("1. Enhanced Smart Agent Test (full functionality)")
    print("2. Quantity Intelligence Test (quantity conversion only)")
    print("3. Both tests")
    
    choice = input("Enter choice (1-3): ").strip()
    
    if choice == "1":
        test_enhanced_smart_agent()
    elif choice == "2":
        test_quantity_intelligence()
    elif choice == "3":
        test_quantity_intelligence()
        test_enhanced_smart_agent()
    else:
        print("Invalid choice. Running both tests.")
        test_quantity_intelligence()
        test_enhanced_smart_agent()
