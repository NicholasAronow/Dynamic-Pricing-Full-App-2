#!/usr/bin/env python3
"""
Restaurant Menu Scraper - AI-Powered Menu Extraction System

This module provides intelligent restaurant menu extraction using:
- OpenAI for search optimization and content extraction
- Google Custom Search API for finding restaurant websites
- Selenium fallback for JavaScript-heavy sites
- AI-powered menu cleanup and deduplication

Key Features:
- Single AI-optimized Google search per restaurant
- Multi-source extraction (up to 3 URLs with valid content)
- Smart URL validation and content filtering
- Higher price priority in duplicate resolution
- Comprehensive error handling with intelligent fallbacks

Usage:
    python3 restaurant_menu_scraper.py "Restaurant Name" --location "City" --use-database

For AI Agent Integration:
    from restaurant_menu_scraper import MenuScraper
    scraper = MenuScraper(openai_api_key="your_key")
    urls = scraper.search_restaurant("Restaurant", "Location")
    menu_items = scraper.scrape_square_menu(urls[0])
    cleaned_items = scraper.cleanup_menu_with_ai(menu_items)
"""

import requests
from bs4 import BeautifulSoup
import argparse
import logging
from urllib.parse import urlparse
import time
import json
import os
import sys
from typing import List, Dict, Optional
from openai import OpenAI
from menu_database import MenuDatabase

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import SessionLocal
import models
import schemas
from services.competitor_entity_service import CompetitorEntityService


class MenuScraper:
    """
    AI-Powered Restaurant Menu Scraper

    This class provides comprehensive restaurant menu extraction using multiple AI-powered
    methods with intelligent fallbacks. Designed for seamless integration with other AI agents.

    Architecture:
        1. AI-optimized Google search for restaurant discovery
        2. Multi-source extraction (up to 3 URLs with valid content)
        3. OpenAI web search → Selenium fallback → Generic HTML parsing
        4. AI-powered menu cleanup with higher price priority
        5. Comprehensive error handling and rate limiting

    Key Features:
        - Single optimized Google search per restaurant (90% API reduction)
        - Smart URL validation (only processes URLs with actual menu content)
        - PDF menu support included in search results
        - AI cleanup prioritizes higher prices for similar items
        - Built-in quota management and retry logic

    Usage for AI Agents:
        scraper = MenuScraper(openai_api_key="your_key")
        urls = scraper.search_restaurant("Restaurant Name", "Location")
        menu_items = scraper.scrape_square_menu(urls[0])
        cleaned_items = scraper.cleanup_menu_with_ai(menu_items)

    Performance Limits:
        - MAX_API_CALLS_PER_SESSION: 30
        - MAX_FAILED_EXTRACTIONS: 5
        - MAX_SITES_TO_PROCESS: 15
        - EXTRACTION_TIMEOUT: 30 seconds
    """

    def __init__(self, openai_api_key=None):
        """
        Initialize the MenuScraper with AI integration.

        Args:
            openai_api_key (str, optional): OpenAI API key. If None, will attempt
                                          to load from environment or README.md

        Sets up:
            - HTTP session with browser-like headers
            - OpenAI client for AI-powered operations
            - Rate limiting and quota management
            - Error tracking and fallback mechanisms
        """
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })

        # OpenAI API credentials
        self.openai_api_key = openai_api_key or os.getenv('OPENAI_API_KEY')

        # API call tracking to prevent excessive usage
        self.api_call_count = 0
        self.max_api_calls_per_session = 30  # Limit API calls per scraping session
        self.failed_extractions = 0
        self.max_failed_extractions = 5  # Stop trying after too many failures
        self.max_sites_to_process = 15  # Limit number of sites to process

        if not self.openai_api_key:
            logging.warning("OpenAI API key not provided. Search functionality will be limited.")
            self.openai_client = None
        else:
            try:
                self.openai_client = OpenAI(api_key=self.openai_api_key)
            except Exception as e:
                logging.error(f"Failed to initialize OpenAI client: {e}")
                self.openai_client = None
    
    def search_restaurant(self, restaurant_name, location=""):
        """Search for a specific restaurant using Google Search API with AI-optimized search term"""
        logging.info(f"Searching for {restaurant_name} {location}")

        # Use AI to generate optimal search term
        search_term = self._generate_optimal_search_term(restaurant_name, location)

        # Perform single Google search with optimized term
        logging.info(f"Searching with Google: {search_term}")
        urls = self._search_with_google(search_term)

        # Remove duplicates, keep up to 10 URLs
        seen = set()
        unique_urls = []
        for url in urls:
            if url not in seen and len(unique_urls) < 10:
                seen.add(url)
                unique_urls.append(url)

        logging.info(f"Found {len(unique_urls)} potential URLs for {restaurant_name}")
        return unique_urls

    def _generate_optimal_search_term(self, restaurant_name: str, location: str) -> str:
        """Use OpenAI to generate an optimal search term for Google"""
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "user",
                    "content": f"""
Create the best Google search term to find menu information for this restaurant:

Restaurant: {restaurant_name}
Location: {location}

Return only the search term, nothing else. The search term should be optimized to find:
1. Official restaurant websites with menus
2. Menu PDFs
3. Food delivery platforms with menus
4. Restaurant review sites with menu information
5. Multiple results with menus from search queries

Example responses:
Joe's Pizza NYC menu
Starbucks Princeton NJ menu PDF
McDonald's menu site:mcdonalds.com

Search term:"""
                }],
                max_tokens=50,
                temperature=0
            )

            search_term = response.choices[0].message.content.strip()
            logging.info(f"AI generated search term: {search_term}")
            return search_term

        except Exception as e:
            logging.warning(f"Failed to generate optimal search term: {e}")
            # Fallback to simple search term
            return f"{restaurant_name} {location} menu"

    def _can_make_api_call(self):
        """Check if we can make another API call within limits"""
        if self.api_call_count >= self.max_api_calls_per_session:
            logging.warning(f"Reached maximum API calls limit ({self.max_api_calls_per_session})")
            return False
        if self.failed_extractions >= self.max_failed_extractions:
            logging.warning(f"Too many failed extractions ({self.failed_extractions}), stopping API calls")
            return False
        return True

    def _search_with_google(self, query):
        """Use Google Search API to find restaurant websites"""
        try:
            from googleapiclient.discovery import build
            import os

            # Get Google API credentials
            api_key = os.getenv('GOOGLE_API_KEY')
            search_engine_id = os.getenv('GOOGLE_SEARCH_ENGINE_ID')

            if not api_key or not search_engine_id:
                logging.error("Google API key or Search Engine ID not found in environment variables")
                return []

            # Build the service
            service = build("customsearch", "v1", developerKey=api_key)

            # Perform the search
            result = service.cse().list(
                q=query,
                cx=search_engine_id,
                num=10  # Get up to 10 results per query
            ).execute()

            urls = []
            if 'items' in result:
                for item in result['items']:
                    url = item['link']
                    # Include PDF files for menu extraction, but skip other file types
                    excluded_extensions = ['.doc', '.docx', '.jpg', '.png', '.gif', '.zip']
                    if any(url.lower().endswith(ext) for ext in excluded_extensions):
                        logging.debug(f"Skipping file URL: {url}")
                        continue

                    # Log PDF files specifically
                    if url.lower().endswith('.pdf'):
                        logging.info(f"Found menu PDF: {url}")
                    else:
                        logging.info(f"Found restaurant URL: {url}")

                    urls.append(url)

            return urls

        except ImportError:
            logging.error("Google API client not installed. Run: pip install google-api-python-client")
            return []
        except Exception as e:
            logging.error(f"Google search error: {e}")
            return []





    def _extract_menu_items_generic(self, soup):
        """Extract menu items using generic patterns"""
        import re

        menu_items = []

        # Remove script and style elements to avoid extracting JSON data
        for script in soup(["script", "style", "noscript"]):
            script.decompose()

        # Pattern 1: Look for structured menu sections first
        menu_items.extend(self._extract_structured_menu_items(soup))

        # Pattern 2: Look for price patterns ($X.XX) and nearby text (only if no structured items found)
        if len(menu_items) < 3:
            price_pattern = re.compile(r'\$\d+\.\d{2}')  # More specific: require 2 decimal places

            # Find all elements containing prices
            price_elements = soup.find_all(string=price_pattern)

            for price_text in price_elements:
                price_match = price_pattern.search(price_text)
                if price_match:
                    price = price_match.group()

                    # Try to find the item name near the price
                    parent = price_text.parent if hasattr(price_text, 'parent') else None
                    item_name = self._find_item_name_near_price(parent, price_text)

                    if item_name and self._is_valid_menu_item_name(item_name):
                        menu_items.append({
                            'name': item_name.strip(),
                            'price': price,
                            'description': ''
                        })

        # Clean and filter items
        cleaned_items = []
        seen = set()

        for item in menu_items:
            # Clean the item name and price
            clean_name = self._clean_item_name(item['name'])
            clean_price = self._clean_price(item['price'])

            if clean_name and clean_price and self._is_valid_menu_item_name(clean_name):
                key = (clean_name.lower(), clean_price)
                if key not in seen:
                    seen.add(key)
                    cleaned_items.append({
                        'name': clean_name,
                        'price': clean_price,
                        'description': item.get('description', '')
                    })

        return cleaned_items

    def _is_valid_menu_item_name(self, name):
        """Check if a name looks like a valid menu item"""
        if not name or len(name.strip()) < 3:
            return False

        # Filter out JSON-like content
        if name.startswith('{') or name.startswith('['):
            return False

        # Filter out very long strings (likely descriptions or JSON)
        if len(name) > 50:
            return False

        # Filter out strings with lots of special characters
        special_char_ratio = sum(1 for c in name if not c.isalnum() and c not in ' -&()') / len(name)
        if special_char_ratio > 0.3:
            return False

        return True

    def _clean_item_name(self, name):
        """Clean up item name"""
        import re
        if not name:
            return ""

        # Remove extra whitespace
        name = re.sub(r'\s+', ' ', name).strip()

        # Remove common prefixes/suffixes
        name = re.sub(r'^(item|product|dish):\s*', '', name, flags=re.IGNORECASE)

        # Limit length
        if len(name) > 50:
            name = name[:50].strip()

        return name

    def _clean_price(self, price):
        """Clean up price string"""
        import re
        if not price:
            return ""

        # Extract just the price part
        price_match = re.search(r'\$\d+\.\d{2}', price)
        if price_match:
            return price_match.group()

        # Fallback for other price formats
        price_match = re.search(r'\$\d+\.?\d*', price)
        if price_match:
            return price_match.group()

        return price

    def _extract_menu_with_openai(self, url, page_text):
        """Use OpenAI Responses API to extract menu items from page text"""
        try:
            extraction_prompt = f"""
            Extract menu items and prices from this restaurant website content.

            Website: {url}
            Content: {page_text}

            Find all food and drink items with prices. Return only the item name and price.
            Format: Item Name - $Price (one per line)

            If you cannot find any menu items or prices, respond with exactly: "NO_MENU_FOUND_TOKEN"

            Example response:
            Margherita Pizza - $12.99
            Caesar Salad - $8.50
            Coffee - $3.00
            """

            # Use the Responses API for better content analysis
            self.api_call_count += 1
            response = self.openai_client.responses.create(
                model="gpt-4.1",
                input=extraction_prompt
            )

            response_text = response.output_text
            logging.debug(f"OpenAI menu extraction response: {response_text}")

            # Check for failure token
            if "NO_MENU_FOUND_TOKEN" in response_text:
                logging.info(f"OpenAI could not extract menu from {url}")
                return []

            # Parse the response into structured menu items
            menu_items = []
            lines = response_text.split('\n')

            for line in lines:
                line = line.strip()
                if not line or line.startswith('#') or line.lower() == "no menu found":
                    continue

                # Parse format: "Item Name - $Price"
                import re
                pattern = r'^(.+?)\s*-\s*\$(\d+\.?\d*)$'
                match = re.match(pattern, line)

                if match:
                    name = match.group(1).strip()
                    price = f"${match.group(2)}"

                    # Clean up name
                    name = re.sub(r'^[-•*]\s*', '', name)  # Remove bullet points
                    name = re.sub(r'^\d+\.\s*', '', name)  # Remove numbering

                    if name and len(name) > 2 and len(name) < 100:
                        menu_items.append({
                            'name': name,
                            'price': price,
                            'description': ''  # No descriptions needed
                        })

            logging.info(f"OpenAI extracted {len(menu_items)} menu items")
            return menu_items  # Return all items found

        except Exception as e:
            logging.error(f"OpenAI menu extraction error: {e}")
            return []

    def _extract_menu_with_web_search(self, url):
        """Use OpenAI web search to directly extract menu content from a restaurant URL"""
        try:
            # Extract restaurant name from URL for better search
            import re
            url_parts = url.split('/')
            restaurant_name = ""
            for part in url_parts:
                if any(keyword in part.lower() for keyword in ['restaurant', 'cafe', 'pizza', 'burger']):
                    restaurant_name = part.replace('-', ' ').replace('_', ' ')
                    break

            if not restaurant_name:
                # Try to extract from the last meaningful part of URL
                meaningful_parts = [part for part in url_parts if part and part not in ['online', 'order', 'local', 'www', 'toasttab', 'com']]
                if meaningful_parts:
                    restaurant_name = meaningful_parts[-1].replace('-', ' ').replace('_', ' ')

            search_prompt = f"""
            Extract the complete menu with prices from this restaurant website: {url}

            Restaurant: {restaurant_name}

            This is a slow-loading or dynamic website. Please search for and extract ALL menu items with their prices.
            Look for breakfast, lunch, dinner, drinks, appetizers, desserts, and any other food items. If there is a menu PDF, download and extract that.

            Format each item as: Item Name - $Price
            Include ALL items you find, not just a sample.

            Example format:
            Margherita Pizza - $12.99
            Caesar Salad - $8.50
            Grilled Chicken Sandwich - $14.50
            Coffee - $3.00
            Chocolate Cake - $6.99

            If the website is loading or you cannot access the menu, respond with exactly: "NO_MENU_FOUND_TOKEN"
            """

            # Use the Responses API with web search
            self.api_call_count += 1
            response = self.openai_client.responses.create(
                model="gpt-4.1",
                tools=[{
                    "type": "web_search_preview",
                    "search_context_size": "high"  # Use high context for better menu extraction
                }],
                input=search_prompt
            )

            response_text = response.output_text
            logging.debug(f"OpenAI web search menu extraction response: {response_text}")

            # Check for failure token
            if "NO_MENU_FOUND_TOKEN" in response_text:
                logging.info("OpenAI web search could not find current menu information")
                return []

            # Check if AI found actual menu information (legacy check)
            if "no menu found" in response_text.lower() or "can't find" in response_text.lower():
                logging.info("OpenAI web search could not find current menu information")
                return []

            # Parse the response into structured menu items
            menu_items = []
            lines = response_text.split('\n')

            for line in lines:
                line = line.strip()
                if not line or line.startswith('#') or line.lower() == "no menu found":
                    continue

                # Parse format: "Item Name - $Price"
                pattern = r'^(.+?)\s*-\s*\$(\d+\.?\d*)$'
                match = re.match(pattern, line)

                if match:
                    name = match.group(1).strip()
                    price = f"${match.group(2)}"

                    # Clean up name
                    name = re.sub(r'^[-•*]\s*', '', name)  # Remove bullet points
                    name = re.sub(r'^\d+\.\s*', '', name)  # Remove numbering

                    if name and len(name) > 2 and len(name) < 100:
                        menu_items.append({
                            'name': name,
                            'price': price,
                            'description': ''  # No descriptions needed
                        })

            logging.info(f"OpenAI web search extracted {len(menu_items)} menu items")
            return menu_items  # Return all items found

        except Exception as e:
            logging.error(f"OpenAI web search menu extraction error: {e}")
            return []

    def _find_item_name_near_price(self, element, _):
        """Find item name near a price element"""
        if not element:
            return ""

        # Try to get text from the same element
        element_text = element.get_text() if hasattr(element, 'get_text') else str(element)

        # Remove the price from the text to get the item name
        import re
        price_pattern = re.compile(r'\$\d+\.?\d*')
        item_text = price_pattern.sub('', element_text).strip()

        # Clean up the text
        item_text = re.sub(r'\s+', ' ', item_text)  # Normalize whitespace
        item_text = item_text.strip(' -•·')  # Remove common separators

        # If text is too short, try parent elements
        if len(item_text) < 3 and hasattr(element, 'parent'):
            parent_text = element.parent.get_text() if element.parent else ""
            parent_text = price_pattern.sub('', parent_text).strip()
            parent_text = re.sub(r'\s+', ' ', parent_text)
            if len(parent_text) > len(item_text):
                item_text = parent_text

        return item_text[:100]  # Limit length

    def _extract_structured_menu_items(self, soup):
        """Extract menu items from structured HTML"""
        menu_items = []

        # Common menu item selectors
        selectors = [
            # Generic menu item patterns
            '.menu-item', '.menu_item', '.menuitem',
            '.product', '.product-item', '.item',
            '.food-item', '.dish', '.meal',
            # Common e-commerce patterns
            '.product-card', '.product-tile', '.item-card',
            # Restaurant-specific patterns
            '[class*="menu"]', '[class*="item"]', '[class*="product"]'
        ]

        for selector in selectors:
            try:
                items = soup.select(selector)
                for item in items:
                    name_elem = self._find_name_element(item)
                    price_elem = self._find_price_element(item)

                    if name_elem and price_elem:
                        name = name_elem.get_text().strip()
                        price = price_elem.get_text().strip()

                        if name and price and '$' in price:
                            menu_items.append({
                                'name': name[:100],
                                'price': price,
                                'description': ''
                            })
            except Exception as e:
                logging.debug(f"Error with selector {selector}: {e}")
                continue

        return menu_items

    def _find_name_element(self, item):
        """Find name element within a menu item"""
        # Try common name selectors
        name_selectors = ['h1', 'h2', 'h3', 'h4', 'h5', '.name', '.title', '.product-name', '.item-name']

        for selector in name_selectors:
            elem = item.select_one(selector)
            if elem and elem.get_text().strip():
                return elem

        # Fallback: use the item itself if it's a text element
        text = item.get_text().strip()
        if text and len(text) < 100:
            return item

        return None

    def _find_price_element(self, item):
        """Find price element within a menu item"""
        import re

        # Try common price selectors
        price_selectors = ['.price', '.cost', '.amount', '[class*="price"]', '[class*="cost"]']

        for selector in price_selectors:
            elem = item.select_one(selector)
            if elem and '$' in elem.get_text():
                return elem

        # Fallback: look for any element with $ in the text
        price_pattern = re.compile(r'\$\d+\.?\d*')
        for elem in item.find_all(text=price_pattern):
            if elem.parent:
                return elem.parent

        return None
    
    def scrape_square_menu(self, url):
        """Scrape menu from restaurant site (handles redirects and uses OpenAI for extraction)"""
        try:
            # Follow redirects and get final URL with longer timeout for slow sites
            response = self.session.get(url, allow_redirects=True, timeout=30)
            final_url = response.url
            logging.info(f"Following redirect from {url} to {final_url}")

            soup = BeautifulSoup(response.content, 'html.parser')

            menu_items = []

            # Only use web search extraction method
            if self.openai_client and self._can_make_api_call():
                logging.info(f"Using web search extraction for {final_url}")
                ai_items = self._extract_menu_with_web_search(final_url)

                if ai_items:
                    menu_items.extend(ai_items)
                    logging.info(f"Web search extraction found {len(ai_items)} items")
                else:
                    logging.info(f"Web search extraction found no items for {final_url}")
                    self.failed_extractions += 1

                    # If web search failed, try Selenium as fallback
                    if len(menu_items) == 0 and self.failed_extractions <= 3:
                        logging.info(f"Web search failed, trying Selenium fallback for {final_url}")
                        selenium_items = self._extract_with_selenium_fallback(final_url)
                        if selenium_items:
                            menu_items.extend(selenium_items)
                            logging.info(f"Selenium fallback succeeded with {len(selenium_items)} items")

            elif not self._can_make_api_call():
                logging.warning(f"API call limit reached, skipping extraction for {final_url}")

            logging.info(f"Extracted {len(menu_items)} menu items from {final_url}")
            return menu_items

        except Exception as e:
            logging.error(f"Error scraping menu from {url}: {e}")
            return []

    def _extract_with_selenium_fallback(self, url):
        """Fallback method using Selenium for JavaScript-heavy sites"""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            # Setup Chrome options for headless browsing
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")

            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(30)

            logging.info(f"Using Selenium fallback for {url}")
            driver.get(url)

            # Wait for page to load and look for menu content
            wait = WebDriverWait(driver, 15)

            # Wait for common menu indicators to appear
            menu_selectors = [
                "div[class*='menu']", "div[class*='item']", "div[class*='product']",
                ".menu", ".menu-item", ".product", ".item", "[data-testid*='menu']"
            ]

            for selector in menu_selectors:
                try:
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    break
                except:
                    continue

            # Get page content after JavaScript execution
            page_source = driver.page_source
            driver.quit()

            # Parse with BeautifulSoup and extract menu items
            soup = BeautifulSoup(page_source, 'html.parser')
            menu_items = self._extract_menu_items_generic(soup)

            # If still no items, try OpenAI on the rendered content
            if len(menu_items) < 3 and self.openai_client and self._can_make_api_call():
                page_text = soup.get_text()[:5000].strip()
                if len(page_text) > 100:  # Only if we got meaningful content
                    ai_items = self._extract_menu_with_openai(url, page_text)
                    menu_items.extend(ai_items)

            return menu_items

        except ImportError:
            logging.warning("Selenium not available. Install with: pip install selenium")
            return []
        except Exception as e:
            logging.error(f"Selenium fallback failed for {url}: {e}")
            return []
    


    def cleanup_menu_with_ai(self, menu_items):
        """Clean up menu items using OpenAI to remove duplicates and fix formatting"""
        if not self.openai_client or not menu_items:
            return menu_items

        try:
            # Convert menu items to a single string
            menu_string = "\n".join([f"{item['name']} - ${item['price']}" for item in menu_items])

            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "user",
                    "content": f"""
Clean up this restaurant menu by:
1. Remove duplicate items - if there are two items that are similar or the same, keep the one with the HIGHER price
2. Remove invalid items (non-food/drink items)
3. Ensure consistent format: "Item Name - $Price"
4. Fix any formatting issues

Important: When you find similar items with different prices (e.g., "Coffee - $3.00" and "Coffee - $4.50"), always keep the one with the higher price ($4.50 in this example).

Menu:
{menu_string}

Return only the cleaned menu items, one per line, in the format "Item Name - $Price"
"""
                }],
                max_tokens=2000,
                temperature=0
            )

            cleaned_menu_text = response.choices[0].message.content.strip()

            # Parse the cleaned menu back into the expected format
            cleaned_items = []
            for line in cleaned_menu_text.split('\n'):
                line = line.strip()
                if ' - $' in line:
                    name, price_part = line.rsplit(' - $', 1)
                    try:
                        price = float(price_part)
                        cleaned_items.append({
                            'name': name.strip(),
                            'price': price,
                            'description': '',
                            'category': ''
                        })
                    except ValueError:
                        continue

            logging.info(f"Menu cleanup: {len(menu_items)} → {len(cleaned_items)} items")
            return cleaned_items if cleaned_items else menu_items

        except Exception as e:
            logging.error(f"Error cleaning menu with AI: {e}")
            return menu_items
    
    def save_competitor_data(self, competitor_name: str, location: str, menu_items: List[Dict], 
                           website_url: str = None, user_id: int = None) -> Dict:
        """
        Save competitor data using the main application database and CompetitorEntityService
        
        Args:
            competitor_name: Name of the competitor restaurant
            location: Location/address of the competitor
            menu_items: List of menu items with name, price, description, category
            website_url: URL of the competitor's website
            user_id: User ID (required for main database)
            
        Returns:
            Dict with competitor_id, items_added, and success status
        """
        try:
            logging.info(f"💾 Starting save_competitor_data for {competitor_name}")
            logging.info(f"👤 User ID: {user_id}")
            logging.info(f"📍 Location: {location}")
            logging.info(f"🔗 Website: {website_url}")
            logging.info(f"🍽️ Menu items count: {len(menu_items)}")
            
            # Create database session
            db = SessionLocal()
            logging.info("✅ Database session created")
            
            try:
                # Validate user_id is provided
                if not user_id:
                    raise ValueError("user_id is required when saving to main database")
                
                # Verify user exists
                logging.info(f"🔍 Checking if user {user_id} exists...")
                user = db.query(models.User).filter(models.User.id == user_id).first()
                if not user:
                    raise ValueError(f"User with ID {user_id} not found")
                logging.info(f"✅ User {user.email} found")
                
                # Initialize competitor entity service
                logging.info("🛠️ Initializing CompetitorEntityService...")
                comp_service = CompetitorEntityService(db)
                
                # Create competitor entity
                competitor_data_dict = {
                    'name': competitor_name,
                    'address': location,
                    'category': 'restaurant',
                    'website': website_url,
                    'menu_url': website_url,
                    'is_selected': True
                }
                
                logging.info(f"🏪 Creating competitor entity with data: {competitor_data_dict}")
                # Create schema object and call service with correct argument order
                competitor_data = schemas.CompetitorEntityCreate(**competitor_data_dict)
                competitor_entity = comp_service.create_competitor_entity(competitor_data, user_id)
                competitor_id = competitor_entity.id
                logging.info(f"✅ Competitor entity created with ID: {competitor_id}")
                
                # Prepare menu items for database
                logging.info(f"📝 Processing {len(menu_items)} menu items...")
                items_to_add = []
                skipped_items = 0
                
                for i, item in enumerate(menu_items):
                    item_data = {
                        'item_name': item.get('name', '').strip(),
                        'price': float(item.get('price', 0)) if item.get('price') else None,
                        'description': item.get('description', '').strip(),
                        'category': item.get('category', '').strip(),
                        'competitor_id': competitor_id
                    }
                    
                    # Only add items with valid names
                    if item_data['item_name']:
                        items_to_add.append(item_data)
                        if i < 3:  # Log first 3 items for debugging
                            logging.info(f"  Item {i+1}: {item_data['item_name']} - ${item_data['price']} - {item_data['category']}")
                    else:
                        skipped_items += 1
                        logging.warning(f"  Skipping item {i+1} - no name: {item}")
                
                logging.info(f"✅ Prepared {len(items_to_add)} valid items (skipped {skipped_items})")
                
                # Add competitor items to database
                logging.info("💾 Adding items to database...")
                items_added = 0
                for i, item_data in enumerate(items_to_add):
                    try:
                        competitor_item = models.CompetitorItem(**item_data)
                        db.add(competitor_item)
                        items_added += 1
                        if i < 3:  # Log first 3 successful additions
                            logging.info(f"  Added item {i+1}: {item_data['item_name']}")
                    except Exception as item_error:
                        logging.warning(f"Failed to add item {item_data.get('item_name')}: {item_error}")
                        continue
                
                logging.info(f"💾 Committing {items_added} items to database...")
                # Commit all changes
                db.commit()
                logging.info("✅ Database commit successful")
                
                # Debug: Print structured database output
                print("\n" + "="*80)
                print("🗃️  MAIN DATABASE OUTPUT - DEBUG")
                print("="*80)
                print(f"CompetitorEntity:")
                print(f"  ID: {competitor_entity.id}")
                print(f"  User ID: {competitor_entity.user_id}")
                print(f"  Name: {competitor_entity.name}")
                print(f"  Address: {competitor_entity.address}")
                print(f"  Category: {competitor_entity.category}")
                print(f"  Website: {competitor_entity.website}")
                print(f"  Menu URL: {competitor_entity.menu_url}")
                print(f"  Is Selected: {competitor_entity.is_selected}")
                print(f"  Created At: {competitor_entity.created_at}")
                print(f"\nCompetitorItems Added: {items_added} items")
                
                # Show first 5 items as sample
                sample_items = db.query(models.CompetitorItem).filter(
                    models.CompetitorItem.competitor_id == competitor_id
                ).limit(5).all()
                
                for i, item in enumerate(sample_items, 1):
                    print(f"  Item {i}:")
                    print(f"    ID: {item.id}")
                    print(f"    Competitor ID: {item.competitor_id}")
                    print(f"    Name: {item.item_name}")
                    print(f"    Price: ${item.price:.2f}" if item.price else "    Price: N/A")
                    print(f"    Category: {item.category or 'N/A'}")
                    print(f"    Description: {item.description or 'N/A'}")
                    print()
                
                if items_added > 5:
                    print(f"  ... and {items_added - 5} more items")
                print("="*80)
                
                logging.info(f"Saved competitor {competitor_name} with {items_added} items to main database")
                
                return {
                    'competitor_id': competitor_id,
                    'items_added': items_added,
                    'success': True
                }
                
            finally:
                db.close()
            
        except Exception as e:
            logging.error(f"Error saving competitor data to main database: {e}")
            return {
                'competitor_id': None,
                'items_added': 0,
                'success': False,
                'error': str(e)
            }

def main():

    parser = argparse.ArgumentParser(description='Scrape restaurant menu using OpenAI web search')
    parser.add_argument('restaurant_name', help='Name of the restaurant (e.g., "Joe\'s Pizza", "Starbucks")')
    parser.add_argument('--location', help='Optional location to narrow search (e.g., "New York")', default='')
    parser.add_argument('--output', '-o', help='Output JSON file', default='menus.json')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    parser.add_argument('--use-database', action='store_true', help='Store results in database instead of JSON file')
    parser.add_argument('--db-path', default='restaurant_menus.db', help='Database file path')
    parser.add_argument('--use-competitor-db', action='store_true', help='Store results in competitor database using new models')
    parser.add_argument('--user-id', type=int, help='User ID for saving to main database')

    args = parser.parse_args()

    logging.basicConfig(level=args.log_level, format='%(levelname)s %(message)s')

    # Initialize scraper
    scraper = MenuScraper()

    # Search for the specific restaurant
    urls = scraper.search_restaurant(args.restaurant_name, args.location)

    if not urls:
        error_msg = f"No URLs found for {args.restaurant_name}"
        logging.error(error_msg)
        print(f"\n❌ {error_msg}")
        sys.exit(1)

    logging.info(f"Found {len(urls)} potential URLs for {args.restaurant_name}")

    # Try to scrape menu from URLs until we find 3 that have menu items
    all_menu_items = []
    successful_urls = []
    max_successful_urls = 3

    for i, url in enumerate(urls):
        if len(successful_urls) >= max_successful_urls:
            break

        try:
            logging.info(f"Attempting to scrape URL {i+1}: {url}")
            items = scraper.scrape_square_menu(url)
            if items:
                all_menu_items.extend(items)
                successful_urls.append(url)
                logging.info(f"Successfully scraped {len(items)} items from {url}")
                logging.info(f"Found {len(successful_urls)}/{max_successful_urls} URLs with menu items")
            else:
                logging.info(f"No menu items found at {url}")
        except Exception as e:
            logging.warning(f"Failed to scrape {url}: {e}")

    if not all_menu_items:
        error_msg = f"Could not extract menu from any URL for {args.restaurant_name}"
        logging.error(error_msg)
        print(f"\n❌ {error_msg}")
        print(f"   🔍 Tried {len(urls)} URLs but found no menu items")
        print(f"   📝 This could mean:")
        print(f"     - The restaurant doesn't have an online menu")
        print(f"     - The menu is behind a login/paywall")
        print(f"     - The website structure is not supported")
        sys.exit(1)

    logging.info(f"Total items collected from {len(successful_urls)} URLs with menu content: {len(all_menu_items)}")
    menu_items = all_menu_items
    successful_url = successful_urls[0] if successful_urls else urls[0]  # Use first successful URL for reference

    # Clean up the menu using AI
    logging.info("Cleaning up menu with AI...")
    menu_items = scraper.cleanup_menu_with_ai(menu_items)

    # Prepare menu data
    menu_data = {
        'restaurant_name': args.restaurant_name,
        'url': successful_url,
        'menu_items': menu_items,
        'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S')
    }

    # Save results
    if args.use_competitor_db:
        # Save to main application database
        logging.info(f"🗃️ Saving {len(menu_items)} menu items to main database for user {args.user_id}")
        
        result = scraper.save_competitor_data(
            competitor_name=args.restaurant_name,
            location=args.location or '',
            menu_items=menu_items,
            website_url=successful_url,
            user_id=args.user_id
        )
        
        logging.info(f"💾 Save result: {result}")
        
        if result['success']:
            logging.info(f"✅ Saved competitor {args.restaurant_name} with {result['items_added']} items")
            print(f"\n✅ Successfully scraped {args.restaurant_name}!")
            print(f"   📍 Found {result['items_added']} menu items")
            print(f"   🔗 Source: {successful_url}")
            print(f"   🆔 Competitor ID: {result['competitor_id']}")
        else:
            logging.error(f"❌ Failed to save {args.restaurant_name} to main database: {result.get('error')}")
            print(f"\n❌ Failed to save competitor data: {result.get('error')}")
    elif args.use_database:
        # Save to legacy database
        db = MenuDatabase(args.db_path)

        # Create a search record first
        search_id = db.create_search_record('restaurant', args.location or '')

        # Prepare restaurant data in the format expected by store_restaurant_menu
        restaurant_data = {
            'site': successful_url,
            'platform': 'Other',  # Generic platform
            'menu': menu_items
        }

        # Store the restaurant and menu
        success = db.store_restaurant_menu(search_id, restaurant_data)

        if success:
            logging.info(f"Saved {args.restaurant_name} with {len(menu_items)} menu items to database")
            print(f"\n✅ Successfully scraped {args.restaurant_name}!")
            print(f"   📍 Found {len(menu_items)} menu items")
            print(f"   🔗 Source: {successful_url}")
        else:
            logging.error(f"Failed to save {args.restaurant_name} to database")
    else:
        # Save to JSON file
        with open(args.output, 'w') as f:
            json.dump(menu_data, f, indent=2)

        logging.info(f"Saved {args.restaurant_name} with {len(menu_items)} menu items to {args.output}")
        print(f"\n✅ Successfully scraped {args.restaurant_name}!")
        print(f"   📍 Found {len(menu_items)} menu items")
        print(f"   🔗 Source: {successful_url}")
        print(f"   💾 Saved to: {args.output}")

if __name__ == '__main__':
    main()