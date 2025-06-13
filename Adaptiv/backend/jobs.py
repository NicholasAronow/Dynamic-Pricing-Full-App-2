import os
import logging
from redis import Redis
from rq import Queue
from rq.job import Job
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.orm import Session
from database import engine, SessionLocal

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("jobs")

# Redis connection
redis_conn = Redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))
queue = Queue('default', connection=redis_conn)

# Create jobs table if it doesn't exist
def setup_jobs_table():
    try:
        with engine.connect() as connection:
            # Check if the jobs table exists
            table_exists_query = text(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'job_status'
                );
                """
            )
            table_exists = connection.execute(table_exists_query).scalar()
            
            if not table_exists:
                logger.info("Creating job_status table...")
                create_table_query = text(
                    """
                    CREATE TABLE job_status (
                        id SERIAL PRIMARY KEY,
                        job_id VARCHAR(255) NOT NULL,
                        report_id INTEGER,
                        status VARCHAR(50) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        error TEXT
                    );
                    """
                )
                connection.execute(create_table_query)
                connection.commit()
                logger.info("job_status table created successfully")
    except Exception as e:
        logger.error(f"Error setting up jobs table: {str(e)}")


def queue_menu_extraction(report_id, force_refresh=False):
    """Queue up a menu extraction job"""
    # No need to import extract_menu_items, it's defined in this module
    
    logger.info(f"Queueing menu extraction job for report_id: {report_id}")
    
    # Queue the job
    job = queue.enqueue(
        extract_menu_in_background,
        args=(report_id, force_refresh),
        job_timeout='10m'  # 10 minute timeout for extraction
    )
    
    # Store job ID in database
    try:
        db = SessionLocal()
        query = text(
            """
            INSERT INTO job_status (job_id, report_id, status)
            VALUES (:job_id, :report_id, 'queued');
            """
        )
        db.execute(query, {"job_id": job.id, "report_id": report_id})
        db.commit()
        logger.info(f"Job {job.id} queued for report_id {report_id}")
    except Exception as e:
        logger.error(f"Error storing job status: {str(e)}")
    finally:
        db.close()
    
    return job.id


def extract_menu_items(db, report_id, force_refresh=False):
    """Extract menu items for a competitor report"""
    # Import here to avoid circular imports
    import json
    from models import CompetitorReport
    import google.generativeai as genai
    import os
    
    # Set up Gemini API key from environment variable
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY not found in environment variables")
        # Fall back to a default key if available (not recommended for production)
        api_key = os.environ.get("GOOGLE_API_KEY")
        
    if api_key:
        genai.configure(api_key=api_key)
    else:
        return {"success": False, "error": "Gemini API key not configured", "menu_items": []}

    try:
        # Create Gemini model
        model = genai.GenerativeModel('gemini-2.5-pro-preview-06-05')
        
        # Get competitor details
        competitor_report = db.query(CompetitorReport).filter(CompetitorReport.id == report_id).first()
        if not competitor_report:
            return {"success": False, "error": "Competitor report not found", "menu_items": []}
        
        competitor_data = competitor_report.competitor_data
        competitor_name = competitor_data.get("name", "")
        competitor_category = competitor_data.get("category", "")
        direct_menu_url = competitor_data.get("menu_url")
        
        # If a direct menu URL is provided, use that instead of searching
        if direct_menu_url:
            logger.info(f"Using direct menu URL: {direct_menu_url}")
            source_urls = [{"url": direct_menu_url, "confidence": "high"}]
            competitor = {
                "name": competitor_name,
                "category": competitor_category,
                "report_id": report_id
            }
        else:
            # Step 1: Find menu URLs using Gemini
            step1_prompt = f"""TASK: Find online menu URLs for {competitor_name}, which is a {competitor_category} business.

RETURN DATA AS JSON ARRAY:
[
  {{
    "url": "https://example.com/menu",
    "confidence": "high|medium|low"  # confidence this is a valid menu URL
  }}
]

Include ONLY direct menu URLs (not homepages) and ensure each URL is complete (has https:// or http://).
MAXIMUM 3 URLs with highest confidence.
"""
            
            try:
                # Generate response for Step 1
                step1_response = model.generate_content(step1_prompt)
                step1_text = step1_response.text
                
                if "```json" in step1_text:
                    urls_json = step1_text.split("```json")[1].split("```")[0].strip()
                elif "```" in step1_text:
                    urls_json = step1_text.split("```")[1].strip()
                else:
                    urls_json = step1_text.strip()
                    
                source_urls = json.loads(urls_json)
                
                competitor = {
                    "name": competitor_name,
                    "category": competitor_category,
                    "report_id": report_id
                }
                
                if not source_urls:
                    return {
                        "success": False, 
                        "error": "Could not find any online menu sources", 
                        "competitor": competitor,
                        "menu_items": []
                    }
            except Exception as e:
                logger.error(f"Error finding menu URLs: {str(e)}")
                return {"success": False, "error": f"Error finding menu URLs: {str(e)}", "menu_items": []}
        
        # Step 2: Extract menu items from each URL
        all_menu_items = []
        for source in source_urls:
            url = source.get("url")
            if not url:
                continue
                
            # Extract menu items from URL using Gemini
            step2_prompt = f"""TASK: Extract all menu items and prices from this web page for {competitor_name}.

URL: {url}

RETURN DATA AS JSON ARRAY:
[
  {{
    "item_name": "Exact menu item name",
    "category": "Category from the menu if available",
    "description": "Item description if available",
    "price": 12.99,
    "price_currency": "USD"  # Use appropriate currency code
  }}
]

Only include items with both name and price. Skip items without clear pricing.
Include at least 5 and maximum 50 menu items.
"""
            
            try:
                # Generate response for Step 2
                step2_response = model.generate_content(step2_prompt)
                step2_text = step2_response.text
                
                if "```json" in step2_text:
                    items_json = step2_text.split("```json")[1].split("```")[0].strip()
                elif "```" in step2_text:
                    items_json = step2_text.split("```")[1].strip()
                else:
                    items_json = step2_text.strip()
                
                url_items = json.loads(items_json)
                all_menu_items.extend(url_items)
            except Exception as e:
                logger.error(f"Error extracting menu from URL {url}: {str(e)}")
                # Continue to next URL if this one fails
        
        if not all_menu_items:
            return {
                "success": False,
                "error": "No menu items could be extracted from the found URLs",
                "competitor": competitor,
                "menu_items": []
            }
            
        # Step 3: Consolidate menu data
        step3_prompt = f"""TASK: Consolidate and optimize this menu data for {competitor_name} ({competitor_category}).

INPUT MENU ITEMS:
{json.dumps(all_menu_items, indent=2)}

CONSOLIDATED OUTPUT FORMAT:
[
  {{
    "item_name": "Standardized item name",
    "category": "appetizer|main_course|dessert|beverage|side|special",
    "description": "Best available description or null",
    "price": 12.99,
    "price_currency": "USD",
    "availability": "available|seasonal|limited_time|unknown",
    "source_confidence": "high|medium|low"
  }}
]

RULES:
1. DEDUPLICATE items that are clearly the same product
2. STANDARDIZE item names and categories
3. Use the MOST COMPLETE description available
4. Use the MOST RECENT or MOST COMMON price when multiple exist
5. Add "availability" and "source_confidence" fields based on your assessment
6. Return maximum 30 most representative menu items
7. PRIORITIZE items with complete information (name, category, description, price)

RETURN ONLY THE JSON ARRAY, no explanations."""
        
        try:
            # Generate response for Step 3
            step3_response = model.generate_content(step3_prompt)
            step3_text = step3_response.text
            
            if "```json" in step3_text:
                final_json = step3_text.split("```json")[1].split("```")[0].strip()
            elif "```" in step3_text:
                final_json = step3_text.split("```")[1].strip()
            else:
                final_json = step3_text.strip()
            
            consolidated_items = json.loads(final_json)
        except Exception as e:
            logger.error(f"Error in menu consolidation: {str(e)}")
            # Fallback to raw items if consolidation fails
            consolidated_items = all_menu_items[:30] if len(all_menu_items) > 30 else all_menu_items
        
        # Generate a unique batch ID and current timestamp for this menu sync
        import uuid
        from datetime import datetime
        batch_id = f"{report_id}_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"
        sync_timestamp = datetime.now()
        
        # Save menu items to the database
        from models import CompetitorItem
        saved_items = []
        competitor_address = competitor_data.get("address", "")
        
        for item in consolidated_items:
            try:
                price_str = item.get("price")
                if isinstance(price_str, str):
                    # Remove currency symbols and convert to float
                    price_str = price_str.replace("$", "").replace("€", "").replace("£", "").strip()
                    price_float = float(price_str)
                else:
                    price_float = float(price_str) if price_str else 0.0
                    
                competitor_item = CompetitorItem(
                    competitor_report_id=report_id,
                    item_name=item.get("item_name", ""),
                    category=item.get("category", ""),
                    description=item.get("description") if item.get("description") else None,
                    price=price_float,
                    url=competitor_address,  # Using address as a reference point
                    batch_id=batch_id,
                    sync_timestamp=sync_timestamp
                )
                
                db.add(competitor_item)
                saved_items.append({
                    "item_name": item.get("item_name", ""),
                    "category": item.get("category", ""),
                    "description": item.get("description"),
                    "price": item.get("price"),
                    "price_currency": item.get("price_currency", "USD"),
                    "availability": item.get("availability", "available"),
                    "source_confidence": item.get("source_confidence", "medium")
                })
            except Exception as e:
                logger.error(f"Error saving menu item: {str(e)}")
                # Continue saving other items
                continue
        
        db.commit()
        
        return {
            "success": True,
            "competitor": competitor,
            "menu_items": saved_items,
            "batch": {
                "id": batch_id,
                "timestamp": sync_timestamp.isoformat(),
                "item_count": len(saved_items)
            }
        }
    
    except Exception as e:
        logger.error(f"Error in extract_menu_items: {str(e)}")
        return {"success": False, "error": str(e), "menu_items": []}

def extract_menu_in_background(report_id, force_refresh):
    """Background job for menu extraction"""
    logger.info(f"Starting background menu extraction for report_id: {report_id}")
    
    db = SessionLocal()
    try:
        # Update job status to processing
        update_job_status(db, report_id, "processing")
        
        # Run the extraction - using our own internal function, not importing from gemini_competitor_search
        # to avoid circular imports
        result = extract_menu_items(db, report_id, force_refresh)
        
        # Update job status to completed
        success = result.get("success", False)
        if success:
            update_job_status(db, report_id, "completed")
            logger.info(f"Menu extraction completed for report_id: {report_id}")
        else:
            error_msg = result.get("error", "Unknown error")
            update_job_status(db, report_id, "failed", error_msg)
            logger.error(f"Menu extraction failed for report_id: {report_id}: {error_msg}")
        
        return result
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error in menu extraction job: {error_msg}")
        update_job_status(db, report_id, "failed", error_msg)
        raise e
    
    finally:
        db.close()


def update_job_status(db: Session, report_id: int, status: str, error: str = None):
    """Update job status in the database"""
    try:
        query = text(
            """
            UPDATE job_status
            SET status = :status, updated_at = CURRENT_TIMESTAMP
            WHERE report_id = :report_id AND status != 'completed'
            """
        )
        params = {"status": status, "report_id": report_id}
        
        if error and status == "failed":
            query = text(
                """
                UPDATE job_status
                SET status = :status, updated_at = CURRENT_TIMESTAMP, error = :error
                WHERE report_id = :report_id AND status != 'completed'
                """
            )
            params["error"] = error
            
        db.execute(query, params)
        db.commit()
    except Exception as e:
        logger.error(f"Error updating job status: {str(e)}")
        db.rollback()


def get_job_status(job_id):
    """Get status of a specific job"""
    try:
        # First check RQ job status
        job = Job.fetch(job_id, connection=redis_conn)
        
        # Then check our database for more details
        db = SessionLocal()
        query = text(
            """
            SELECT status, error, report_id
            FROM job_status
            WHERE job_id = :job_id
            ORDER BY updated_at DESC
            LIMIT 1
            """
        )
        result = db.execute(query, {"job_id": job_id}).fetchone()
        db.close()
        
        if result:
            return {
                "job_id": job_id,
                "status": result.status,
                "error": result.error,
                "report_id": result.report_id
            }
        
        # If not in our DB but in Redis
        if job.is_finished:
            return {"job_id": job_id, "status": "completed"}
        elif job.is_failed:
            return {"job_id": job_id, "status": "failed", "error": str(job.exc_info)}
        else:
            return {"job_id": job_id, "status": "processing"}
            
    except Exception as e:
        logger.error(f"Error getting job status: {str(e)}")
        return {"job_id": job_id, "status": "unknown", "error": str(e)}


# Initialize the jobs table
setup_jobs_table()
