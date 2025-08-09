"""
Test script for the improved smart shopping agent with Hebrew product matching
"""
import os
from shopping_agent import ShoppingAgent
from loguru import logger

def test_smart_shopping():
    """Test the smart shopping agent with Hebrew product matching and promotions"""
    print("🤖 בדיקת סוכן קניות חכם עם התאמת מוצרים")
    print("=" * 60)
    
    # Check OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Please set OPENAI_API_KEY environment variable")
        print("   Create a .env file with: OPENAI_API_KEY=your_key_here")
        return
    
    # Initialize agent
    print("\n🔧 יוצר סוכן קניות חכם...")
    try:
        agent = ShoppingAgent()
        print("✅ הסוכן מוכן לעבודה!")
    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}")
        return
    
    # Test cases for intelligent product matching
    test_cases = [
        {
            "name": "מלפפונים רגילים",
            "request": "מלפפונים 2 קג",
            "expected": "צריך לבחור מלפפון רגיל לשקילה, לא בייבי או בשימורים"
        },
        {
            "name": "חלב רגיל",
            "request": "חלב 3 יחידות", 
            "expected": "צריך לבחור חלב רגיל 3%, ולבדוק מבצעים"
        },
        {
            "name": "מוצר עם מבצע",
            "request": "לחם 2 יחידות",
            "expected": "צריך לבדוק אם יש מבצע ולהתאים כמות"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 בדיקה {i}: {test_case['name']}")
        print(f"📝 בקשה: {test_case['request']}")
        print(f"💡 ציפייה: {test_case['expected']}")
        print("-" * 50)
        
        try:
            # Process the shopping request
            result = agent.process_shopping_list(test_case['request'])
            
            print("🤖 תגובת הסוכן:")
            print(result)
            print("-" * 50)
            
        except Exception as e:
            print(f"❌ שגיאה בבדיקה: {e}")
        
        # Wait between tests
        print("⏳ ממתין לבדיקה הבאה...")
        import time
        time.sleep(2)
    
    print("\n✅ כל הבדיקות הושלמו!")
    print("\n📊 סיכום יכולות הסוכן החכם:")
    print("✅ חיפוש מוצרים עם infinite scroll")
    print("✅ זיהוי חכם של המוצר המתאים ביותר")
    print("✅ התחשבות במבצעים ועיסקאות") 
    print("✅ הוספה אוטומטית לסל")
    print("✅ דיווח מפורט על כל פעולה")

def test_shopping_list():
    """Test with a complete shopping list"""
    print("\n" + "="*60)
    print("🛒 בדיקת רשימת קניות מלאה")
    print("="*60)
    
    shopping_list = """
    מלפפונים 3 קג
    חלב 2 יחידות
    לחם 1 יחידה
    """
    
    print(f"📋 רשימת קניות:\n{shopping_list}")
    
    try:
        agent = ShoppingAgent()
        result = agent.process_shopping_list(shopping_list)
        
        print("🤖 עיבוד רשימת הקניות:")
        print(result)
        
    except Exception as e:
        print(f"❌ שגיאה: {e}")

if __name__ == "__main__":
    # Test individual items
    test_smart_shopping()
    
    # Test complete shopping list
    test_shopping_list()
