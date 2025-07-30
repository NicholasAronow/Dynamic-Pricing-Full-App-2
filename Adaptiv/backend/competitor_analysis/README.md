# Restaurant Menu Scraper

An AI-powered Python system that intelligently extracts restaurant menu information from websites using OpenAI and Google Search APIs.

## 🎯 System Overview

This system provides automated restaurant menu extraction with the following architecture:
- **AI-Optimized Search**: Uses OpenAI to generate optimal Google search terms
- **Multi-Source Extraction**: Scrapes up to 3 URLs with valid menu content per restaurant
- **Intelligent Fallback**: OpenAI web search → Selenium browser automation
- **Smart Cleanup**: AI-powered deduplication with higher price priority
- **Persistent Storage**: SQLite database with comprehensive menu management

## 🚀 Quick Start

### Prerequisites
```bash
# Install dependencies
pip install -r requirements.txt
```

### Basic Usage
```bash
# Scrape restaurant menu
python3 restaurant_menu_scraper.py "Restaurant Name" --location "City" --use-database

# View all restaurants
python3 menu_manager.py list

# View specific menu
python3 menu_manager.py menu [ID]
```

## 📋 Core Components

### 1. restaurant_menu_scraper.py
**Main scraping engine with AI optimization**

**Key Classes:**
- `MenuScraper`: Core scraping functionality with AI integration

**Key Methods:**
- `search_restaurant()`: AI-optimized Google search
- `_generate_optimal_search_term()`: OpenAI search term generation
- `scrape_square_menu()`: Multi-method extraction pipeline
- `_extract_menu_with_web_search()`: OpenAI web search extraction
- `_extract_with_selenium_fallback()`: Browser automation fallback
- `cleanup_menu_with_ai()`: AI-powered menu deduplication

**Command Line Interface:**
```bash
python3 restaurant_menu_scraper.py [RESTAURANT_NAME] [OPTIONS]

Options:
  --location TEXT        Location to narrow search (e.g., "New York")
  --use-database        Store in SQLite database (recommended)
  --output FILE         Output JSON file (alternative to database)
  --log-level LEVEL     DEBUG|INFO|WARNING|ERROR (default: INFO)
  --db-path FILE        Database file path (default: restaurant_menus.db)
```

### 2. menu_database.py
**SQLite database management with AI integration**

**Key Classes:**
- `MenuDatabase`: Complete database operations

**Key Methods:**
- `add_restaurant()`: Store restaurant with menu items
- `get_restaurants_by_search()`: Query restaurants by location/type
- `export_menu_data()`: Export complete dataset
- `clear_database()`: Reset all data

**Database Schema:**
```sql
restaurants: id, name, url, platform, location, last_updated
menu_items: id, restaurant_id, name, price, description, category
searches: id, restaurant_name, location, timestamp
```

### 3. menu_manager.py
**CLI tool for database operations**

**Commands:**
```bash
python3 menu_manager.py list                    # List all restaurants
python3 menu_manager.py menu [ID]               # Show restaurant menu
python3 menu_manager.py export                  # Export all data
python3 menu_manager.py clear                   # Clear database
```

## How It Works

1. **Discovery**: Google Search API finds restaurant websites
2. **Extraction**: AI extracts menu items from website content
3. **Storage**: Data saved to SQLite with duplicate detection
4. **Enhancement**: AI cleans names and standardizes formatting

## Output Format

All menu items follow this standard format:
```
Margherita Pizza - $12.99
Caesar Salad - $8.50
Coffee - $3.00
```

## Files

- `restaurant_menu_scraper.py` - Main scraping engine with auto API key loading
- `menu_database.py` - Database operations and AI enhancements
- `menu_manager.py` - CLI management tool with auto API key loading
- `requirements.txt` - Python dependencies

## Requirements

- Python 3.7+
- OpenAI API key (for menu extraction and AI enhancements)
- Google Search API key and Custom Search Engine ID (for finding restaurants)
- Internet connection

## Troubleshooting

**No results found?** Try different restaurant names or enable debug logging:
```bash
python restaurant_menu_scraper.py "Restaurant Name" --location "City" --log-level DEBUG
```

**API errors?** API keys are automatically loaded from this README. If you still get errors, check your OpenAI API key and rate limits.

## Example Workflow

```bash
# 1. Scrape a specific restaurant (API keys loaded automatically)
python restaurant_menu_scraper.py "Starbucks" --location "Princeton NJ" --use-database

# 2. Scrape another restaurant
python restaurant_menu_scraper.py "Joe's Pizza" --location "Princeton NJ" --use-database

# 3. View results
python menu_manager.py list
python menu_manager.py menu 1

# 4. Fix restaurant names with AI (API keys loaded automatically)
python menu_manager.py fix-names

# 5. Standardize menu formatting (API keys loaded automatically)
python menu_manager.py standardize --all

# 6. Export data
python menu_manager.py export princeton_restaurants.json --location "Princeton NJ"
```

## 🔧 System Architecture

### Extraction Pipeline
```
1. AI Search Term Generation → 2. Google Custom Search → 3. URL Validation
                                        ↓
4. OpenAI Web Search ←→ 5. Selenium Fallback ←→ 6. Generic HTML Parsing
                                        ↓
7. AI Menu Cleanup → 8. Database Storage → 9. Result Validation
```

### AI Integration Points
1. **Search Optimization**: OpenAI generates targeted search terms
2. **Content Extraction**: OpenAI web search API extracts menu data
3. **Menu Cleanup**: AI removes duplicates and prioritizes higher prices
4. **Restaurant Name Extraction**: AI identifies canonical restaurant names

### Error Handling & Fallbacks
- **Google Search Failure**: Graceful degradation with basic search terms
- **OpenAI Extraction Failure**: Automatic Selenium browser fallback
- **Selenium Failure**: Generic HTML parsing as final fallback
- **API Rate Limits**: Built-in quota management and retry logic

## 📊 Data Flow

### Input Processing
```
Restaurant Name + Location → AI Search Term → Google URLs → Content Extraction
```

### Output Structure
```json
{
  "restaurant": {
    "id": 1,
    "name": "Restaurant Name",
    "url": "https://example.com",
    "location": "City, State",
    "last_updated": "2025-01-23T00:00:00"
  },
  "menu_items": [
    {
      "name": "Item Name",
      "price": "12.99",
      "description": "Item description",
      "category": "Main Course"
    }
  ]
}
```

## 🛠 Configuration

### API Requirements
- **OpenAI API**: GPT-4o-mini for search optimization and content extraction
- **Google Custom Search**: For finding restaurant websites
- **Chrome Browser**: Required for Selenium fallback functionality

### Performance Settings
```python
# Built-in limits (configurable in code)
MAX_API_CALLS_PER_SESSION = 50
MAX_FAILED_EXTRACTIONS = 5
MAX_SITES_TO_PROCESS = 15
EXTRACTION_TIMEOUT = 30  # seconds
```

## 🔍 Advanced Usage

### Batch Processing
```bash
# Process multiple restaurants
for restaurant in "Pizza Hut" "Dominos" "Papa Johns"; do
    python3 restaurant_menu_scraper.py "$restaurant" --location "New York" --use-database
done
```

### Database Queries
```python
from menu_database import MenuDatabase

db = MenuDatabase()
restaurants = db.get_restaurants_by_search(location="New York")
menu_data = db.export_menu_data()
```

### Custom Integration
```python
from restaurant_menu_scraper import MenuScraper

scraper = MenuScraper(openai_api_key="your_key")
urls = scraper.search_restaurant("Restaurant Name", "Location")
menu_items = scraper.scrape_square_menu(urls[0])
cleaned_items = scraper.cleanup_menu_with_ai(menu_items)
```

## 📁 File Structure
```
competitor_analysis/
├── restaurant_menu_scraper.py    # Main scraping engine
├── menu_database.py              # Database management
├── menu_manager.py               # CLI database operations
├── requirements.txt              # Python dependencies
├── restaurant_menus.db           # SQLite database (auto-created)
├── README.md                     # This documentation
└── CHANGELOG.md                  # Version history
```

## 🚨 Important Notes for AI Agents

### Integration Guidelines
1. **API Keys**: Ensure all three API keys are properly configured
2. **Database Path**: Use absolute paths for database files in production
3. **Error Handling**: Always check return values and handle exceptions
4. **Rate Limiting**: Respect API quotas and implement backoff strategies
5. **Data Validation**: Verify menu items have valid names and prices

### Common Integration Patterns
```python
# Standard workflow
scraper = MenuScraper()
db = MenuDatabase()

# Search and extract
urls = scraper.search_restaurant(name, location)
menu_items = []
for url in urls[:3]:  # Process up to 3 URLs
    items = scraper.scrape_square_menu(url)
    menu_items.extend(items)

# Clean and store
cleaned_items = scraper.cleanup_menu_with_ai(menu_items)
restaurant_id = db.add_restaurant(name, urls[0], "Other", location)
db.store_menu_items(restaurant_id, cleaned_items)
```

### Performance Optimization
- Use `--log-level ERROR` for production to reduce output
- Implement caching for repeated restaurant queries
- Consider parallel processing for batch operations
- Monitor API usage to avoid quota exhaustion

## 🔧 Troubleshooting

### Common Issues
1. **No URLs Found**: Check Google Custom Search Engine configuration
2. **Empty Menu Items**: Verify OpenAI API key and quota
3. **Selenium Errors**: Ensure Chrome browser is installed
4. **Database Errors**: Check file permissions and disk space

### Debug Mode
```bash
python3 restaurant_menu_scraper.py "Restaurant" --location "City" --log-level DEBUG
```

This system is designed for seamless integration with other AI agents and provides comprehensive menu extraction capabilities with intelligent fallbacks and error handling.