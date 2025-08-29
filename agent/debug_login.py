import asyncio
from crawl4ai import AsyncWebCrawler

async def debug_login_page():
    """
    Debug the login page to see what we're working with
    """
    async with AsyncWebCrawler(verbose=True) as crawler:
        # First, just load the login page to see its structure
        result = await crawler.arun(url="https://www.shufersal.co.il/online/he/login")
        
        if result.success:
            print("Login page loaded successfully!")
            print("=" * 80)
            print("Looking for form elements and CSRF tokens...")
            print("=" * 80)
            
            # Look for specific patterns in the HTML
            html = result.html
            
            # Check for CSRF token
            if '_csrf' in html:
                print("✅ CSRF token found in page")
                # Find CSRF token value
                import re
                csrf_match = re.search(r'name="_csrf"[^>]*content="([^"]*)"', html)
                if csrf_match:
                    print(f"CSRF Token: {csrf_match.group(1)}")
            else:
                print("❌ No CSRF token found")
            
            # Check for form fields
            if 'j_username' in html:
                print("✅ Username field (j_username) found")
            else:
                print("❌ Username field not found")
                
            if 'j_password' in html:
                print("✅ Password field (j_password) found")
            else:
                print("❌ Password field not found")
                
            if 'btn-login' in html:
                print("✅ Login button found")
            else:
                print("❌ Login button not found")
            
            # Check for any form action URLs
            if 'action=' in html:
                form_actions = re.findall(r'action="([^"]*)"', html)
                print(f"Form actions found: {form_actions}")
            
            # Save the HTML for manual inspection
            with open('login_page_debug.html', 'w', encoding='utf-8') as f:
                f.write(html)
            print("💾 Full HTML saved to login_page_debug.html for inspection")
            
        else:
            print(f"❌ Failed to load login page: {result.error_message}")

if __name__ == "__main__":
    asyncio.run(debug_login_page())