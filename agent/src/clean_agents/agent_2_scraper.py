"""
Agent 2: Shufersal Web Scraper
Takes product requests and scrapes Shufersal to find all available options
"""
import time
from typing import List, Dict, Any
from dataclasses import dataclass
from loguru import logger
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.shufersal_scraper import ShuferSalScraper, ProductResult
from .agent_1_parser import ProductRequest

@dataclass
class ProductSearchResult:
    """Result of searching for a specific product"""
    original_request: ProductRequest
    found_products: List[ProductResult]
    search_successful: bool
    search_terms_used: str

class ShuferSalScraperAgent:
    """Agent 2: Scrapes Shufersal website to find product options"""
    
    def __init__(self):
        self.agent_name = "Shufersal Scraper Agent"
        self.scraper = ShuferSalScraper(headless=True)
        logger.info(f"🕷️ {self.agent_name} initialized")
    
    def process(self, product_requests: List[ProductRequest]) -> List[ProductSearchResult]:
        """
        Search Shufersal for each product request
        
        Input: List of ProductRequest objects
        Output: List of ProductSearchResult with all found options
        """
        logger.info(f"🕷️ {self.agent_name} processing {len(product_requests)} requests")
        
        search_results = []
        
        for i, request in enumerate(product_requests, 1):
            logger.info(f"🔍 Searching {i}/{len(product_requests)}: {request.product_name}")
            
            try:
                # Search for this product
                result = self._search_single_product(request)
                search_results.append(result)
                
                # Log results
                if result.search_successful:
                    logger.info(f"✅ Found {len(result.found_products)} options for '{request.product_name}'")
                else:
                    logger.warning(f"❌ No products found for '{request.product_name}'")
                
                # Be respectful to the website
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"❌ Search failed for '{request.product_name}': {e}")
                
                # Create failed result
                search_results.append(ProductSearchResult(
                    original_request=request,
                    found_products=[],
                    search_successful=False,
                    search_terms_used=""
                ))
        
        logger.info(f"🕷️ {self.agent_name} completed: {len(search_results)} searches")
        return search_results
    
    def _search_single_product(self, request: ProductRequest) -> ProductSearchResult:
        """Search for a single product using multiple search terms"""
        
        all_found_products = []
        successful_search_term = ""
        
        # Try each search term until we find products
        for search_term in request.search_terms:
            logger.debug(f"🔍 Trying search term: '{search_term}'")
            
            try:
                products = self.scraper.search_product(search_term)
                
                if products:
                    # Filter products based on request criteria
                    filtered_products = self._filter_products(products, request)
                    
                    if filtered_products:
                        all_found_products.extend(filtered_products)
                        successful_search_term = search_term
                        break  # Found products, stop searching
                        
            except Exception as e:
                logger.debug(f"Search term '{search_term}' failed: {e}")
                continue
        
        # Remove duplicates (same product ID)
        unique_products = self._remove_duplicate_products(all_found_products)
        
        return ProductSearchResult(
            original_request=request,
            found_products=unique_products,
            search_successful=len(unique_products) > 0,
            search_terms_used=successful_search_term
        )
    
    def _filter_products(self, products: List[ProductResult], request: ProductRequest) -> List[ProductResult]:
        """Filter products based on request criteria"""
        filtered = []
        
        for product in products:
            # Check brand preference
            if request.brand_preference:
                if request.brand_preference.lower() not in product.name.lower():
                    continue
            
            # Check special notes (like "ללא ביישום")
            if request.special_notes:
                product_matches_notes = True
                for note in request.special_notes:
                    if note not in product.name:
                        product_matches_notes = False
                        break
                
                if not product_matches_notes:
                    continue
            
            # Product passed all filters
            filtered.append(product)
        
        # If no products match filters, return all products (let comparison agent decide)
        return filtered if filtered else products
    
    def _remove_duplicate_products(self, products: List[ProductResult]) -> List[ProductResult]:
        """Remove duplicate products based on product ID"""
        seen_ids = set()
        unique_products = []
        
        for product in products:
            if product.product_id not in seen_ids:
                seen_ids.add(product.product_id)
                unique_products.append(product)
        
        return unique_products
    
    def close(self):
        """Clean up scraper resources"""
        if self.scraper:
            self.scraper.close()
        logger.info(f"🕷️ {self.agent_name} closed")

# Test the agent
if __name__ == "__main__":
    # Import parser agent for testing
    from agent_1_parser import HebrewParserAgent
    
    # Test the scraper agent
    parser_agent = HebrewParserAgent()
    scraper_agent = ShuferSalScraperAgent()
    
    try:
        # Parse a test list
        test_list = "מלפפון חמוץ 1, חלב 2"
        requests = parser_agent.process(test_list)
        
        # Search for products
        search_results = scraper_agent.process(requests)
        
        # Display results
        print(f"\n🕷️ SCRAPER AGENT RESULTS")
        print("=" * 50)
        
        for result in search_results:
            print(f"\nProduct: {result.original_request.product_name}")
            print(f"Search successful: {'✅' if result.search_successful else '❌'}")
            print(f"Search term used: {result.search_terms_used}")
            print(f"Products found: {len(result.found_products)}")
            
            for i, product in enumerate(result.found_products[:3], 1):  # Show first 3
                print(f"  {i}. {product.name} - ₪{product.price} ({product.brand})")
                if product.is_on_sale:
                    print(f"     🏷️ ON SALE (was ₪{product.original_price})")
            
            if len(result.found_products) > 3:
                print(f"  ... and {len(result.found_products) - 3} more")
        
    finally:
        scraper_agent.close()
