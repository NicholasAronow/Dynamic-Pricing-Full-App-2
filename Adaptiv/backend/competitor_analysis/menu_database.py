#!/usr/bin/env python3
"""
Database module for storing and managing restaurant menu data
"""

import sqlite3
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Optional
import logging
import os
from openai import OpenAI


class MenuDatabase:
    def __init__(self, db_path: str = "restaurant_menus.db", openai_api_key: str = None):
        """Initialize the menu database"""
        self.db_path = db_path

        # Initialize OpenAI client for name extraction and menu standardization
        api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        if api_key:
            self.openai_client = OpenAI(api_key=api_key)
        else:
            self.openai_client = None
            logging.warning("No OpenAI API key provided. Restaurant name extraction and menu standardization will be disabled.")

        self.init_database()
    
    def init_database(self):
        """Create database tables if they don't exist"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create searches table to track search parameters
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS searches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    restaurant_type TEXT NOT NULL,
                    location TEXT NOT NULL,
                    search_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    total_sites_found INTEGER DEFAULT 0,
                    successful_extractions INTEGER DEFAULT 0
                )
            ''')
            
            # Create restaurants table to store restaurant information
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS restaurants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    url TEXT UNIQUE NOT NULL,
                    platform TEXT NOT NULL,
                    location TEXT,
                    restaurant_type TEXT,
                    first_scraped DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                    menu_hash TEXT,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')
            
            # Create menu_items table to store individual menu items
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS menu_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    restaurant_id INTEGER NOT NULL,
                    search_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    price TEXT,
                    description TEXT,
                    category TEXT,
                    scraped_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (restaurant_id) REFERENCES restaurants (id),
                    FOREIGN KEY (search_id) REFERENCES searches (id)
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_restaurants_url ON restaurants(url)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_restaurants_type_location ON restaurants(restaurant_type, location)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_menu_items_restaurant ON menu_items(restaurant_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_searches_type_location ON searches(restaurant_type, location)')
            
            conn.commit()
            logging.info("Database initialized successfully")
    
    def create_search_record(self, restaurant_type: str, location: str) -> int:
        """Create a new search record and return its ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO searches (restaurant_type, location)
                VALUES (?, ?)
            ''', (restaurant_type, location))
            search_id = cursor.lastrowid
            conn.commit()
            logging.info(f"Created search record {search_id} for {restaurant_type} in {location}")
            return search_id
    
    def update_search_stats(self, search_id: int, total_sites: int, successful_extractions: int):
        """Update search statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE searches 
                SET total_sites_found = ?, successful_extractions = ?
                WHERE id = ?
            ''', (total_sites, successful_extractions, search_id))
            conn.commit()
    
    def _calculate_menu_hash(self, menu_items: List[Dict]) -> str:
        """Calculate hash of menu items for change detection"""
        menu_str = json.dumps(sorted(menu_items, key=lambda x: x.get('name', '')), sort_keys=True)
        return hashlib.md5(menu_str.encode()).hexdigest()
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL to prevent duplicates from URL variations"""
        from urllib.parse import urlparse, urlunparse

        # Parse the URL
        parsed = urlparse(url.lower().strip())

        # Remove common variations
        path = parsed.path.rstrip('/')
        if not path:
            path = '/'

        # Remove common tracking parameters and fragments
        query = ''  # Remove all query parameters for now to avoid duplicates

        # Reconstruct normalized URL
        normalized = urlunparse((
            parsed.scheme,
            parsed.netloc,
            path,
            '',  # Remove params
            query,
            ''  # Remove fragment
        ))

        return normalized

    def store_restaurant_menu(self, search_id: int, restaurant_data: Dict) -> bool:
        """
        Store restaurant and menu data, completely overwriting existing menus
        Returns True if data was stored, False if no menu items
        """
        url = restaurant_data['site']
        platform = restaurant_data['platform']
        menu_items = restaurant_data['menu']

        if not menu_items:
            logging.info(f"Skipping restaurant with no menu items: {url}")
            return False

        # Normalize URL to prevent duplicates
        normalized_url = self._normalize_url(url)

        # Calculate menu hash for change detection
        menu_hash = self._calculate_menu_hash(menu_items)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Check if restaurant already exists (by normalized URL)
            cursor.execute('SELECT id, menu_hash, name, url FROM restaurants WHERE url = ?', (normalized_url,))
            existing = cursor.fetchone()

            if existing:
                restaurant_id, _, existing_name, _ = existing

                # Always overwrite menu items regardless of hash changes
                # This ensures complete menu replacement every time

                # Update existing restaurant with new data (keep normalized URL)
                cursor.execute('''
                    UPDATE restaurants
                    SET last_updated = CURRENT_TIMESTAMP, menu_hash = ?, platform = ?
                    WHERE id = ?
                ''', (menu_hash, platform, restaurant_id))

                # Delete ALL old menu items for this restaurant
                cursor.execute('DELETE FROM menu_items WHERE restaurant_id = ?', (restaurant_id,))
                deleted_count = cursor.rowcount

                logging.info(f"Overwriting menu for existing restaurant: {existing_name} (deleted {deleted_count} old items)")
            else:
                # Extract restaurant name using AI or fallback to URL parsing
                restaurant_name = self.extract_restaurant_name_with_ai(url)

                # Insert new restaurant with normalized URL
                cursor.execute('''
                    INSERT INTO restaurants (name, url, platform, menu_hash)
                    VALUES (?, ?, ?, ?)
                ''', (restaurant_name, normalized_url, platform, menu_hash))
                restaurant_id = cursor.lastrowid

                logging.info(f"Added new restaurant: {restaurant_name}")

            # Insert ALL new menu items
            for item in menu_items:
                cursor.execute('''
                    INSERT INTO menu_items (restaurant_id, search_id, name, price, description)
                    VALUES (?, ?, ?, ?, ?)
                ''', (restaurant_id, search_id, item.get('name', ''),
                      item.get('price', ''), item.get('description', '')))

            conn.commit()
            logging.info(f"Stored {len(menu_items)} menu items for restaurant ID {restaurant_id}")
            return True
    
    def _extract_restaurant_name(self, url: str) -> str:
        """Extract restaurant name from URL"""
        import re
        from urllib.parse import urlparse
        
        parsed = urlparse(url)
        path_parts = [part for part in parsed.path.split('/') if part]
        
        # Look for meaningful parts in the URL
        for part in path_parts:
            if any(keyword in part.lower() for keyword in ['restaurant', 'cafe', 'pizza', 'burger', 'coffee']):
                # Clean up the name
                name = part.replace('-', ' ').replace('_', ' ')
                name = re.sub(r'[^a-zA-Z0-9\s]', '', name)
                return name.title()
        
        # Fallback to domain name
        domain_parts = parsed.netloc.split('.')
        if len(domain_parts) > 1:
            return domain_parts[0].replace('-', ' ').title()
        
        return "Unknown Restaurant"

    def extract_restaurant_name_with_ai(self, url: str) -> str:
        """Extract restaurant name from URL using OpenAI API"""
        if not self.openai_client:
            return self._extract_restaurant_name(url)

        try:
            prompt = f"""
            Extract the restaurant name from this URL. Return only the restaurant name, nothing else.

            URL: {url}

            Format: Restaurant Name (no quotes, no extra text)

            Example responses:
            Joe's Pizza
            Blue Square Pizza
            Village Cafe
            """

            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50,
                temperature=0
            )

            restaurant_name = response.choices[0].message.content.strip()

            # Clean up the response
            restaurant_name = restaurant_name.replace('"', '').replace("'", '')

            # Validate the response
            if restaurant_name and len(restaurant_name) > 2 and len(restaurant_name) < 100:
                logging.info(f"AI extracted restaurant name: {restaurant_name} from {url}")
                return restaurant_name
            else:
                logging.warning(f"AI returned invalid restaurant name: {restaurant_name}")
                return self._extract_restaurant_name(url)

        except Exception as e:
            logging.error(f"Error extracting restaurant name with AI: {e}")
            return self._extract_restaurant_name(url)

    def standardize_menu_items(self, menu_items: List[Dict]) -> List[Dict]:
        """Standardize menu items using OpenAI API to ensure consistent format"""
        if not self.openai_client or not menu_items:
            return menu_items

        try:
            # Convert menu items to string format
            menu_text = "\n".join([
                f"{item.get('name', '')} - {item.get('price', '')}"
                for item in menu_items if item.get('name')
            ])

            if not menu_text.strip():
                return menu_items

            prompt = f"""
            Standardize these menu items to ensure consistent format. Each line should be exactly:
            Item Name - $Price

            Fix any formatting issues, ensure prices have $ symbol, remove extra characters.
            Return only the standardized menu items, one per line.

            Menu items to standardize:
            {menu_text}

            Example output format:
            Margherita Pizza - $12.99
            Caesar Salad - $8.50
            Coffee - $3.00
            """

            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0
            )

            standardized_text = response.choices[0].message.content.strip()

            # Parse the standardized response back into menu items
            standardized_items = []
            lines = standardized_text.split('\n')

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Parse format: "Item Name - $Price"
                import re
                pattern = r'^(.+?)\s*-\s*\$(\d+\.?\d*)$'
                match = re.match(pattern, line)

                if match:
                    name = match.group(1).strip()
                    price = f"${match.group(2)}"

                    if name and len(name) > 2:
                        standardized_items.append({
                            'name': name,
                            'price': price,
                            'description': ''
                        })

            if standardized_items:
                logging.info(f"AI standardized {len(standardized_items)} menu items")
                return standardized_items
            else:
                logging.warning("AI standardization returned no valid items")
                return menu_items

        except Exception as e:
            logging.error(f"Error standardizing menu items with AI: {e}")
            return menu_items

    def get_restaurants_by_search(self, restaurant_type: str, location: str) -> List[Dict]:
        """Get all restaurants for a specific search criteria"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT r.id, r.name, r.url, r.platform, r.last_updated,
                       COUNT(mi.id) as menu_item_count
                FROM restaurants r
                JOIN menu_items mi ON r.id = mi.restaurant_id
                JOIN searches s ON mi.search_id = s.id
                WHERE s.restaurant_type = ? AND s.location = ?
                GROUP BY r.id, r.name, r.url, r.platform, r.last_updated
                ORDER BY r.last_updated DESC
            ''', (restaurant_type, location))

            restaurants = []
            for row in cursor.fetchall():
                restaurants.append({
                    'id': row[0],
                    'name': row[1],
                    'url': row[2],
                    'platform': row[3],
                    'last_updated': row[4],
                    'menu_item_count': row[5]
                })

            return restaurants

    def get_menu_items(self, restaurant_id: int) -> List[Dict]:
        """Get all menu items for a specific restaurant"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT name, price, description, scraped_timestamp
                FROM menu_items
                WHERE restaurant_id = ?
                ORDER BY name
            ''', (restaurant_id,))

            items = []
            for row in cursor.fetchall():
                items.append({
                    'name': row[0],
                    'price': row[1],
                    'description': row[2],
                    'scraped_timestamp': row[3]
                })

            return items

    def get_search_history(self, limit: int = 50) -> List[Dict]:
        """Get recent search history"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, restaurant_type, location, search_timestamp,
                       total_sites_found, successful_extractions
                FROM searches
                ORDER BY search_timestamp DESC
                LIMIT ?
            ''', (limit,))

            searches = []
            for row in cursor.fetchall():
                searches.append({
                    'id': row[0],
                    'restaurant_type': row[1],
                    'location': row[2],
                    'search_timestamp': row[3],
                    'total_sites_found': row[4],
                    'successful_extractions': row[5]
                })

            return searches

    def export_menu_data(self, restaurant_type: str = None, location: str = None) -> Dict:
        """Export menu data as JSON"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Build query based on filters
            where_clause = ""
            params = []

            if restaurant_type or location:
                where_clause = "WHERE "
                conditions = []
                if restaurant_type:
                    conditions.append("s.restaurant_type = ?")
                    params.append(restaurant_type)
                if location:
                    conditions.append("s.location = ?")
                    params.append(location)
                where_clause += " AND ".join(conditions)

            query = f'''
                SELECT DISTINCT r.id, r.name, r.url, r.platform, r.last_updated
                FROM restaurants r
                JOIN menu_items mi ON r.id = mi.restaurant_id
                JOIN searches s ON mi.search_id = s.id
                {where_clause}
                ORDER BY r.name
            '''

            cursor.execute(query, params)
            restaurants = cursor.fetchall()

            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'filters': {
                    'restaurant_type': restaurant_type,
                    'location': location
                },
                'restaurants': []
            }

            for restaurant in restaurants:
                restaurant_id, name, url, platform, last_updated = restaurant
                menu_items = self.get_menu_items(restaurant_id)

                export_data['restaurants'].append({
                    'id': restaurant_id,
                    'name': name,
                    'url': url,
                    'platform': platform,
                    'last_updated': last_updated,
                    'menu_items': menu_items
                })

            return export_data

    def fix_restaurant_names(self) -> int:
        """Fix all restaurant names in the database using AI extraction"""
        if not self.openai_client:
            logging.error("OpenAI client not available for restaurant name fixing")
            return 0

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get all restaurants
            cursor.execute('SELECT id, name, url FROM restaurants')
            restaurants = cursor.fetchall()

            fixed_count = 0
            for restaurant_id, current_name, url in restaurants:
                # Extract proper name using AI
                new_name = self.extract_restaurant_name_with_ai(url)

                # Only update if the name actually changed and is better
                if new_name != current_name and new_name != "Unknown Restaurant":
                    cursor.execute(
                        'UPDATE restaurants SET name = ? WHERE id = ?',
                        (new_name, restaurant_id)
                    )
                    fixed_count += 1
                    logging.info(f"Updated restaurant {restaurant_id}: '{current_name}' -> '{new_name}'")

            conn.commit()
            logging.info(f"Fixed {fixed_count} restaurant names")
            return fixed_count

    def standardize_restaurant_menu(self, restaurant_id: int) -> bool:
        """Standardize menu items for a specific restaurant using AI"""
        if not self.openai_client:
            logging.error("OpenAI client not available for menu standardization")
            return False

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get current menu items for the restaurant
            cursor.execute('''
                SELECT id, name, price, description
                FROM menu_items
                WHERE restaurant_id = ?
                ORDER BY name
            ''', (restaurant_id,))

            current_items = cursor.fetchall()
            if not current_items:
                logging.info(f"No menu items found for restaurant {restaurant_id}")
                return False

            # Convert to the format expected by standardize_menu_items
            menu_items = []
            for item_id, name, price, description in current_items:
                menu_items.append({
                    'id': item_id,
                    'name': name,
                    'price': price,
                    'description': description
                })

            # Standardize the menu items
            standardized_items = self.standardize_menu_items(menu_items)

            if not standardized_items or len(standardized_items) == 0:
                logging.warning(f"Standardization returned no items for restaurant {restaurant_id}")
                return False

            # Update the database with standardized items
            updated_count = 0
            for i, standardized_item in enumerate(standardized_items):
                if i < len(current_items):
                    item_id = current_items[i][0]  # Get the original item ID

                    cursor.execute('''
                        UPDATE menu_items
                        SET name = ?, price = ?, description = ?
                        WHERE id = ?
                    ''', (
                        standardized_item['name'],
                        standardized_item['price'],
                        standardized_item.get('description', ''),
                        item_id
                    ))
                    updated_count += 1

            conn.commit()
            logging.info(f"Standardized {updated_count} menu items for restaurant {restaurant_id}")
            return True

    def standardize_all_menus(self) -> Dict[str, int]:
        """Standardize menu items for all restaurants"""
        if not self.openai_client:
            logging.error("OpenAI client not available for menu standardization")
            return {'processed': 0, 'successful': 0, 'failed': 0}

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get all restaurant IDs
            cursor.execute('SELECT DISTINCT id FROM restaurants')
            restaurant_ids = [row[0] for row in cursor.fetchall()]

            results = {'processed': 0, 'successful': 0, 'failed': 0}

            for restaurant_id in restaurant_ids:
                results['processed'] += 1
                if self.standardize_restaurant_menu(restaurant_id):
                    results['successful'] += 1
                else:
                    results['failed'] += 1

            logging.info(f"Standardization complete: {results}")
            return results

    def clear_database(self) -> Dict[str, int]:
        """Clear all data from the database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Count records before deletion
            cursor.execute('SELECT COUNT(*) FROM menu_items')
            menu_items_count = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM restaurants')
            restaurants_count = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM searches')
            searches_count = cursor.fetchone()[0]

            # Delete all data
            cursor.execute('DELETE FROM menu_items')
            cursor.execute('DELETE FROM restaurants')
            cursor.execute('DELETE FROM searches')

            # Reset auto-increment counters
            cursor.execute('DELETE FROM sqlite_sequence WHERE name IN ("menu_items", "restaurants", "searches")')

            conn.commit()

            result = {
                'menu_items_deleted': menu_items_count,
                'restaurants_deleted': restaurants_count,
                'searches_deleted': searches_count
            }

            logging.info(f"Database cleared: {result}")
            return result

    def remove_duplicate_restaurants(self) -> int:
        """Remove duplicate restaurants based on normalized URLs"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Find duplicate restaurants by normalized URL
            cursor.execute('''
                SELECT url, COUNT(*) as count, GROUP_CONCAT(id) as ids
                FROM restaurants
                GROUP BY url
                HAVING count > 1
            ''')

            duplicates = cursor.fetchall()
            removed_count = 0

            for url, _, ids_str in duplicates:
                ids = [int(id_str) for id_str in ids_str.split(',')]
                # Keep the first one, remove the rest
                ids_to_remove = ids[1:]

                for restaurant_id in ids_to_remove:
                    # Delete menu items first
                    cursor.execute('DELETE FROM menu_items WHERE restaurant_id = ?', (restaurant_id,))
                    # Delete restaurant
                    cursor.execute('DELETE FROM restaurants WHERE id = ?', (restaurant_id,))
                    removed_count += 1
                    logging.info(f"Removed duplicate restaurant ID {restaurant_id} for URL {url}")

            conn.commit()
            logging.info(f"Removed {removed_count} duplicate restaurants")
            return removed_count
