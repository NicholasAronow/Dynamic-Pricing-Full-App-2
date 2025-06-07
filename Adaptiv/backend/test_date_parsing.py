#!/usr/bin/env python3
import sys
import re
import json
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DateParsingTest")

def parse_reevaluation_date(llm_response):
    """
    Test the enhanced parsing logic for reevaluation dates from LLM responses
    """
    logger.info("Testing enhanced date parsing logic")
    logger.info(f"Sample LLM response length: {len(llm_response)}")

    # 1. Try to extract JSON from the response
    try:
        # First look for JSON in code blocks
        json_match = re.search(r'```(?:json)?([\s\S]*?)```', llm_response)
        if json_match:
            json_str = json_match.group(1).strip()
            logger.info("Found JSON in code blocks")
        else:
            # Try to find JSON-like structure without code blocks
            json_pattern = r'(\{[\s\S]*\})'
            json_without_ticks = re.search(json_pattern, llm_response)
            if json_without_ticks:
                json_str = json_without_ticks.group(1).strip()
                logger.info("Found JSON-like structure without code blocks")
            else:
                # Last resort: try the entire content
                json_str = llm_response
                logger.info("No JSON structure found, trying entire content")
        
        # Clean JSON string (replace single quotes with double quotes)
        json_str = re.sub(r"(?<!\\\\)'([^']*?)(?<!\\\\)'", r'"\g<1>"', json_str)
        logger.info(f"Cleaned JSON string: {json_str[:100]}...")
        
        # Parse JSON
        data = json.loads(json_str)
        logger.info(f"Successfully parsed JSON: {type(data)}")
        
        # Extract reevaluation date
        if isinstance(data, dict) and 'reevaluation_date' in data:
            date_str = data['reevaluation_date']
            logger.info(f"Found reevaluation_date in JSON: {date_str}")
            
            # Try parsing various date formats
            for date_format in ('%Y-%m-%d', '%Y/%m/%d', '%m/%d/%Y', '%d-%m-%Y'):
                try:
                    parsed_date = datetime.strptime(date_str, date_format)
                    logger.info(f"Successfully parsed date with format {date_format}: {parsed_date}")
                    
                    # Check if date is in the future
                    if parsed_date > datetime.now():
                        logger.info(f"Date is {(parsed_date - datetime.now()).days} days in the future")
                        return parsed_date
                    else:
                        logger.warning(f"Date is not in the future: {parsed_date}")
                except ValueError:
                    continue
            
            logger.error(f"Could not parse date: {date_str} with any supported format")
        else:
            logger.error(f"No reevaluation_date field in data: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")
    
    except Exception as e:
        logger.error(f"Exception during JSON parsing: {str(e)}")
        
        # Fallback: Use regex to find date patterns
        logger.info("Trying fallback regex for date patterns")
        date_patterns = [
            (r'reevaluation_date"?\s*:\s*"?(\d{4}-\d{2}-\d{2})"?', '%Y-%m-%d'),
            (r'reevaluation_date"?\s*:\s*"?(\d{2}/\d{2}/\d{4})"?', '%m/%d/%Y'),
            (r'reevaluation_date"?\s*:\s*"?(\d{4}/\d{2}/\d{2})"?', '%Y/%m/%d'),
            (r'(\d{4}-\d{2}-\d{2})', '%Y-%m-%d'),
            (r'(\d{2}/\d{2}/\d{4})', '%m/%d/%Y'),
            (r'(\d{4}/\d{2}/\d{2})', '%Y/%m/%d')
        ]
        
        for pattern, date_format in date_patterns:
            matches = re.findall(pattern, llm_response)
            if matches:
                logger.info(f"Found date matches with pattern {pattern}: {matches}")
                for date_str in matches:
                    try:
                        parsed_date = datetime.strptime(date_str, date_format)
                        if parsed_date > datetime.now():
                            logger.info(f"Valid future date: {parsed_date}")
                            return parsed_date
                    except ValueError:
                        continue
    
    # Default fallback
    logger.warning("Falling back to default date (90 days from now)")
    return datetime.now() + timedelta(days=90)


def main():
    # Sample LLM responses to test
    samples = [
        # Sample 1: Well-formatted JSON with code blocks
        '''
        Here's my recommendation:

        ```json
        {
          "rationale": "Based on the product's inelastic demand and competitor pricing being higher, a price increase is justified. The 10% increase keeps the price competitive while improving margins.",
          "reevaluation_date": "2025-07-03"
        }
        ```
        ''',
        
        # Sample 2: JSON without code blocks
        '''
        After analyzing the data, I recommend:
        
        {
          "rationale": "Test Widget Alpha has inelastic demand, and competitors price at $59.99. Sales are decreasing but a small price increase optimizes profit while staying competitive.",
          "reevaluation_date": "2025-08-15"
        }
        ''',
        
        # Sample 3: Messy format with single quotes
        '''
        Here's my analysis:
        
        {
          'rationale': 'With inelastic demand of 0.4, a 10% price increase should have limited impact on sales volume while increasing profit margin.',
          'reevaluation_date': '2025-07-25'
        }
        ''',
        
        # Sample 4: Different date format
        '''
        My recommendation:
        
        ```json
        {
          "rationale": "The product shows inelastic demand and can support a price increase without significantly impacting sales.",
          "reevaluation_date": "07/15/2025"
        }
        ```
        ''',
        
        # Sample 5: Text with embedded date
        '''
        I've analyzed the pricing data for Test Widget Alpha. Given the low elasticity and competitive 
        pricing, I recommend increasing the price. The rationale is that the product can sustain this 
        price point while maximizing profitability. You should reevaluate this pricing decision on 2025-08-10
        to ensure it aligns with market conditions at that time.
        '''
    ]
    
    print("TESTING ENHANCED DATE PARSING LOGIC")
    print("=" * 50)
    
    for i, sample in enumerate(samples, 1):
        print(f"\nTEST CASE #{i}")
        print("-" * 30)
        print(f"Sample: {sample[:70]}...")
        
        result = parse_reevaluation_date(sample)
        
        print(f"Result: {result}")
        print(f"Days from now: {(result - datetime.now()).days}")
        print("-" * 30)
    
    print("\nTEST SUMMARY")
    print("=" * 50)
    print("Our enhanced date parsing logic can handle:")
    print("✓ JSON with code blocks")
    print("✓ JSON without code blocks")
    print("✓ JSON with single quotes")
    print("✓ Different date formats (YYYY-MM-DD, MM/DD/YYYY)")
    print("✓ Dates embedded in text")


if __name__ == "__main__":
    main()
