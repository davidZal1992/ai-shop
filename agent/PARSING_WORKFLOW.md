# 🛒 Shopping List Parsing Workflow

## Overview
The enhanced shopping agent now includes intelligent Hebrew shopping list parsing that converts raw user input into structured JSON objects before processing. This ensures accurate product matching, brand recognition, and preference handling.

## 🔄 Complete Workflow

### 1. **Raw Input** (User provides Hebrew shopping list)
```
"מגבונים לתינוק של בייביסיטר ללא בישום 4 חבילות, חלב תנובה 3% 2 יחידות"
```

### 2. **Structured Parsing** (LLM converts to JSON)
```json
[
  {
    "name": "מגבונים לתינוק",
    "quantity": 4,
    "unit": "package",
    "brand": "בייביסיטר",
    "preferences": "ללא בישום"
  },
  {
    "name": "חלב",
    "quantity": 2,
    "unit": "unit",
    "brand": "תנובה",
    "specifications": "3%"
  }
]
```

### 3. **Intelligent Shopping** (For each parsed item)
- Search Shufersal with exact product name
- Filter results based on parsed specifications
- Apply brand preferences and special requirements
- Optimize for promotions while respecting constraints
- Add to cart with precise quantities

## 📊 Parsing Capabilities

### **Product Names**
- Extracts core product name without brand/specs
- `"גבינת עמק 9%"` → `"גבינה"`
- `"מגבונים לתינוק של בייביסיטר"` → `"מגבונים לתינוק"`

### **Quantity Conversion**
- `"חצי קילו"` → `0.5`
- `"רבע קילו"` → `0.25`
- `"קילו וחצי"` → `1.5`
- `"4 חבילות"` → `4`

### **Unit Recognition**
- `"kg"` - kilograms
- `"gram"` - grams  
- `"unit"` - individual items
- `"package"` - packaged items
- `"bottle"` - bottles

### **Brand Extraction**
- `"של בייביסיטר"` → `"בייביסיטר"`
- `"גבינת עמק"` → `"עמק"`
- `"חלב תנובה"` → `"תנובה"`

### **Specifications**
- `"9%"` - fat percentage
- `"500 גרם"` - specific weight
- `"אורגני"` - organic

### **Preferences**
- `"ללא בישום"` - fragrance-free
- `"אורגני"` - organic preference
- `"ארוז"` - packaged/any weight

## 🎯 Real-World Examples

### Example 1: Complex Baby Product
**Input:** `"מגבונים לתינוק של בייביסיטר ללא בישום 4 חבילות"`

**Parsed:**
```json
{
  "name": "מגבונים לתינוק",
  "quantity": 4,
  "unit": "package", 
  "brand": "בייביסיטר",
  "preferences": "ללא בישום"
}
```

**Agent Behavior:**
1. Search "מגבונים לתינוק" on Shufersal
2. Filter ONLY בייביסיטר brand
3. Filter ONLY fragrance-free options
4. Add 4 packages to cart
5. Explain brand and preference matching

### Example 2: Multiple Items with Different Specs
**Input:** `"חלב תנובה 3% 2 יחידות, מלפפונים חצי קילו"`

**Parsed:**
```json
[
  {
    "name": "חלב",
    "quantity": 2,
    "unit": "unit",
    "brand": "תנובה", 
    "specifications": "3%"
  },
  {
    "name": "מלפפונים",
    "quantity": 0.5,
    "unit": "kg"
  }
]
```

**Agent Behavior:**
1. **For חלב:** Search → Filter תנובה 3% → Check promotions → Add optimized quantity
2. **For מלפפונים:** Search → Choose regular cucumbers → Add 0.5 kg
3. Explain promotion optimization and quantity conversion

### Example 3: Brand-Specific with Fat Percentage
**Input:** `"גבינת עמק 9% 500 גרם"`

**Parsed:**
```json
{
  "name": "גבינה",
  "quantity": 500,
  "unit": "gram",
  "brand": "עמק",
  "specifications": "9%"
}
```

**Agent Behavior:**
1. Search "גבינה" but filter for עמק brand only
2. ONLY consider 9% fat options
3. Find closest to 500g size
4. IGNORE cheaper alternatives (user specified עמק)
5. Add to cart with brand justification

## 🔧 Technical Implementation

### **ParseShoppingListTool**
- Uses GPT-4o for intelligent Hebrew parsing
- Converts raw text to structured JSON
- Handles complex Hebrew expressions
- Extracts all relevant product attributes

### **Enhanced Agent Workflow**
1. **PARSE:** `parse_shopping_list` tool converts raw input
2. **SEARCH:** `search_shufersal` for each parsed item
3. **FILTER:** Apply parsed specifications and preferences  
4. **OPTIMIZE:** Find best deals within constraints
5. **EXECUTE:** `add_to_cart` with precise quantities
6. **EXPLAIN:** Reference original parsed requirements

### **Smart Quantity Handling**
- Server uses +/- buttons for precise quantity setting
- Handles decimal weights (0.5, 0.25, 1.5)
- Calculates exact button clicks needed
- Supports both weight-based and unit-based products

## 🎉 Benefits

✅ **Accurate Parsing** - Understands complex Hebrew expressions  
✅ **Brand Loyalty** - Respects specific brand requests  
✅ **Preference Handling** - Applies special requirements  
✅ **Quantity Intelligence** - Converts Hebrew to precise decimals  
✅ **Promotion Optimization** - Finds best deals within specifications  
✅ **Clear Traceability** - Links final choices to original requirements  

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Test complete parsing workflow
python test_parsing_workflow.py

# Test individual parsing only  
python test_parsing_workflow.py
# Choose option 2

# Test enhanced agent with parsing
python test_enhanced_agent.py
```

The parsing workflow transforms raw Hebrew shopping lists into intelligent, structured shopping experiences! 🎯🛒
