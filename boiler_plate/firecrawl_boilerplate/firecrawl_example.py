from firecrawl import FirecrawlApp, JsonConfig
from pydantic import BaseModel
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Initialize Firecrawl with API key
app = FirecrawlApp(api_key=os.getenv("FIRECRAWL_API_KEY"))

class ExtractSchema(BaseModel):
    """Schema for extracting structured data"""
    title: str
    main_content: str
    key_points: list[str]
    has_contact_info: bool
    has_pricing: bool
    target_audience: str

def scrape_with_formats(url: str):
    """
    Scrape a website with multiple output formats
    """
    try:
        # Scrape with multiple formats
        scrape_result = app.scrape_url(
            url,
            formats=['markdown', 'html', 'rawHtml', 'screenshot', 'links']
        )
        print("\nScrape Result with Multiple Formats:")
        print("=" * 50)
        print(scrape_result)
        return scrape_result
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return None

def extract_structured_data(url: str):
    """
    Extract structured data from a website using LLM
    """
    try:
        # Configure JSON extraction
        json_config = JsonConfig(schema=ExtractSchema)
        
        # Scrape with JSON format
        result = app.scrape_url(
            url,
            formats=["json"],
            json_options=json_config,
            only_main_content=False,
            timeout=120000
        )
        
        print("\nStructured Data Extraction Result:")
        print("=" * 50)
        print(result.json)
        return result.json
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return None

if __name__ == "__main__":
    # Test URL
    test_url = "https://www.ibm.com/think/topics/ai-agents"
    print(f"Testing scraping on: {test_url}")
    
    # Test multiple formats
    print("\n1. Testing multiple formats...")
    scrape_with_formats(test_url)
    
    # Test structured data extraction
    print("\n2. Testing structured data extraction...")
    extract_structured_data(test_url) 