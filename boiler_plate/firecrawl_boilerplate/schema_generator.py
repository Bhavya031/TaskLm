from firecrawl import FirecrawlApp
from dotenv import load_dotenv
import os
import openai
import json
from typing import Dict, Any

# Load environment variables
load_dotenv()

# Initialize Firecrawl with API key
app = FirecrawlApp(api_key=os.getenv("FIRECRAWL_API_KEY"))

# Initialize OpenAI client
openai.api_key = os.getenv("OPENAI_API_KEY")

def get_html_content(url: str) -> str:
    """
    Get HTML content from a URL using Firecrawl
    """
    try:
        # Scrape with HTML format
        scrape_result = app.scrape_url(
            url,
            formats=['html']
        )
        
        if hasattr(scrape_result, 'html'):
            return scrape_result.html
        return None
    except Exception as e:
        print(f"Error getting HTML content: {str(e)}")
        return None

def generate_schema_with_openai(html_content: str) -> Dict[str, Any]:
    """
    Generate a schema using OpenAI's model
    """
    try:
        # Prepare the prompt for OpenAI
        prompt = f"""Given this HTML content, create a Pydantic schema for extracting structured data.
        Focus on the main content, key information, and important metadata.
        Return only the schema in Python code format.
        
        HTML Content:
        {html_content[:2000]}  # Limiting content to avoid token limits
        """
        
        # Call OpenAI API
        response = openai.chat.completions.create(
            model="gpt-4",  # or "gpt-3.5-turbo" if you prefer
            messages=[
                {"role": "system", "content": "You are a helpful assistant that creates Pydantic schemas for web content extraction."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        if response.choices:
            return response.choices[0].message.content
        return None
            
    except Exception as e:
        print(f"Error generating schema: {str(e)}")
        return None

def create_schema_for_url(url: str) -> Dict[str, Any]:
    """
    Main function to create a schema for a given URL
    """
    print(f"\nProcessing URL: {url}")
    
    # Step 1: Get HTML content
    print("\n1. Fetching HTML content...")
    html_content = get_html_content(url)
    if not html_content:
        print("Failed to get HTML content")
        return None
    
    # Step 2: Generate schema
    print("\n2. Generating schema with OpenAI...")
    schema = generate_schema_with_openai(html_content)
    if not schema:
        print("Failed to generate schema")
        return None
    
    # Step 3: Save schema to file
    try:
        filename = f"generated_schema_{url.replace('https://', '').replace('/', '_')}.py"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(schema)
        print(f"\nSchema saved to: {filename}")
    except Exception as e:
        print(f"Error saving schema: {str(e)}")
    
    return schema

if __name__ == "__main__":
    # Test URL
    test_url = "https://www.ibm.com/think/topics/ai-agents"
    print("Starting schema generation process...")
    
    # Generate schema
    schema = create_schema_for_url(test_url)
    
    if schema:
        print("\nGenerated Schema:")
        print("=" * 50)
        print(schema) 