# Competitor Database Usage Guide

This document explains how to use the new SQLAlchemy-based competitor database models that were added to track competitors and their menu items.

## New Database Models

### CompetitorEntity
Tracks actual competitor restaurants with the following fields:
- `id`: Primary key
- `user_id`: Foreign key to users table
- `name`: Competitor name
- `address`: Physical address
- `category`: Restaurant category
- `phone`: Phone number
- `website`: Website URL
- `distance_km`: Distance from user location
- `latitude/longitude`: GPS coordinates
- `menu_url`: URL where menu was scraped from
- `score`: Relevance/similarity score
- `is_selected`: Whether competitor is selected for tracking

### CompetitorItem
Maps menu items to competitors with the following fields:
- `id`: Primary key
- `competitor_id`: Foreign key to competitor_entities
- `competitor_name`: Competitor name (for backward compatibility)
- `item_name`: Menu item name
- `description`: Item description
- `category`: Item category
- `price`: Item price (as float)
- `similarity_score`: Similarity to comparable items
- `url`: Source URL
- `batch_id`: Unique identifier for menu fetch batch
- `sync_timestamp`: When this batch was synced

## Usage Examples

### 1. Scraping with New Database Format

```bash
# Scrape a restaurant and save to competitor database
python3 restaurant_menu_scraper.py "Joe's Pizza" --location "New York" --use-competitor-db

# This will:
# - Create a CompetitorEntity for "Joe's Pizza"
# - Add all menu items as CompetitorItem records
# - Link them with batch tracking and timestamps
```

### 2. Managing Competitor Data

```bash
# View all competitors
python3 competitor_manager.py view

# View only selected competitors
python3 competitor_manager.py view --selected-only

# View menu items for a specific competitor
python3 competitor_manager.py items 1

# View only the latest batch of items
python3 competitor_manager.py items 1 --latest-only

# Get summary of all competitors
python3 competitor_manager.py summary

# Scrape and save a new competitor
python3 competitor_manager.py scrape "McDonald's" --location "San Francisco"
```

### 3. Programmatic Usage

```python
from competitor_database import CompetitorDatabase
from restaurant_menu_scraper import MenuScraper

# Initialize database
comp_db = CompetitorDatabase()

# Create or get user
user_id = comp_db.create_or_get_user()

# Create competitor entity
competitor_id = comp_db.create_competitor_entity(
    user_id=user_id,
    name="Test Restaurant",
    address="123 Main St",
    category="Italian",
    is_selected=True
)

# Add menu items
menu_items = [
    {"name": "Pizza", "price": 15.99, "category": "Main", "description": "Cheese pizza"},
    {"name": "Salad", "price": 8.99, "category": "Appetizer", "description": "Caesar salad"}
]

comp_db.add_competitor_items(competitor_id, menu_items)

# Get competitor summary
summary = comp_db.get_competitor_summary(user_id)
print(summary)
```

## Key Features

1. **Batch Tracking**: Each menu scrape creates a unique batch_id, allowing you to track when items were added and compare different scraping sessions.

2. **Automatic Cleanup**: Old batches are automatically cleaned up, keeping only the 3 most recent batches per competitor.

3. **User-based**: All competitors are tied to a user_id, allowing for multi-user support in the future.

4. **Backward Compatibility**: The original MenuDatabase is still supported via the `--use-database` flag.

5. **Comprehensive Management**: The competitor_manager.py tool provides easy ways to view and manage all competitor data.

## Database Files

- `competitor_analysis.db`: New SQLAlchemy-based database with CompetitorEntity and CompetitorItem tables
- `restaurant_menus.db`: Original SQLite database (still supported for backward compatibility)

## Migration

The new system runs alongside the existing system. To migrate existing data, you would need to:

1. Export data from the old `restaurant_menus.db`
2. Transform it to match the new CompetitorEntity/CompetitorItem structure
3. Import it using the CompetitorDatabase class

The new system is recommended for all new competitor tracking as it provides better organization and more comprehensive features.
