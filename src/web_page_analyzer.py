import os
import json
import logging
from typing import Dict, List, Optional, Any
from firecrawl import FirecrawlApp
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebPageAnalyzer:
    """Analyzes web pages to understand their structure and available data types"""
    
    def __init__(self):
        self.firecrawl_app = None
        self.openai_client = None
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize Firecrawl and OpenAI clients"""
        try:
            firecrawl_key = os.getenv("FIRECRAWL_API_KEY")
            openai_key = os.getenv("OPENAI_API_KEY")
            
            if firecrawl_key:
                self.firecrawl_app = FirecrawlApp(api_key=firecrawl_key)
                logger.info("Firecrawl client initialized")
            else:
                logger.warning("FIRECRAWL_API_KEY not found")
            
            if openai_key:
                self.openai_client = openai.OpenAI(api_key=openai_key)
                logger.info("OpenAI client initialized")
            else:
                logger.warning("OPENAI_API_KEY not found")
                
        except Exception as e:
            logger.error(f"Error initializing clients: {str(e)}")
    
    def get_page_content(self, url: str) -> Optional[str]:
        """Get HTML content from a URL using Firecrawl"""
        if not self.firecrawl_app:
            logger.error("Firecrawl client not initialized")
            return None
            
        try:
            logger.info(f"Fetching content from: {url}")
            scrape_result = self.firecrawl_app.scrape_url(
                url,
                formats=['html', 'markdown']
            )
            
            # Try to get markdown first (cleaner), then HTML
            if hasattr(scrape_result, 'markdown') and scrape_result.markdown:
                return scrape_result.markdown
            elif hasattr(scrape_result, 'html') and scrape_result.html:
                return scrape_result.html
            else:
                logger.error("No content found in scrape result")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching page content: {str(e)}")
            return None
    
    def analyze_page_structure(self, url: str) -> Dict[str, Any]:
        """Analyze a web page to understand its structure and available data types"""
        
        # Get page content
        content = self.get_page_content(url)
        if not content:
            return {
                "success": False,
                "error": "Could not fetch page content",
                "url": url
            }
        
        # Analyze with GPT-4o
        analysis = self._analyze_with_gpt(content, url)
        
        return {
            "success": True,
            "url": url,
            "analysis": analysis,
            "content_preview": content[:500] + "..." if len(content) > 500 else content
        }
    
    def _analyze_with_gpt(self, content: str, url: str) -> Dict[str, Any]:
        """Use GPT-4o to analyze page structure and identify data types"""
        
        if not self.openai_client:
            return {"error": "OpenAI client not initialized"}
        
        try:
            # Limit content to avoid token limits
            limited_content = content[:3000] if len(content) > 3000 else content
            
            system_prompt = """You are a web scraping analyst. Analyze the provided web page content and identify what types of data are available for extraction.

Focus on:
1. Main content types (articles, products, listings, etc.)
2. Specific data fields that could be extracted
3. Repeated patterns or structured data
4. Navigation elements and page structure
5. Any forms, tables, or structured content

Respond in JSON format:
{
    "page_type": "e-commerce|news|blog|directory|social|forum|other",
    "main_content_type": "description of primary content",
    "extractable_data": {
        "primary_fields": ["field1", "field2", "field3"],
        "secondary_fields": ["optional_field1", "optional_field2"],
        "metadata_fields": ["date", "author", "category"]
    },
    "data_patterns": {
        "repeated_elements": "description of repeated content",
        "structured_data": "tables, lists, cards, etc.",
        "navigation": "menu, pagination, filters"
    },
    "scraping_complexity": "simple|moderate|complex",
    "recommended_approach": "description of best scraping strategy",
    "data_richness": "high|medium|low",
    "key_insights": ["insight1", "insight2", "insight3"]
}"""

            user_prompt = f"""Analyze this web page content from URL: {url}

Content:
{limited_content}

Provide a detailed analysis of what data can be extracted from this page."""

            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=1500
            )
            
            if response.choices and response.choices[0].message.content:
                analysis = json.loads(response.choices[0].message.content)
                logger.info(f"Successfully analyzed page: {url}")
                return analysis
            else:
                logger.error("No response from OpenAI")
                return {"error": "No analysis generated"}
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {str(e)}")
            return {"error": "Failed to parse analysis"}
        except Exception as e:
            logger.error(f"Error in GPT analysis: {str(e)}")
            return {"error": f"Analysis failed: {str(e)}"}
    
    def analyze_multiple_urls(self, urls: List[str]) -> Dict[str, Any]:
        """Analyze multiple URLs and provide a combined analysis"""
        results = {}
        
        for url in urls:
            logger.info(f"Analyzing URL: {url}")
            results[url] = self.analyze_page_structure(url)
        
        # Generate combined insights
        combined_analysis = self._generate_combined_insights(results)
        
        return {
            "individual_analyses": results,
            "combined_insights": combined_analysis,
            "total_urls": len(urls),
            "successful_analyses": sum(1 for r in results.values() if r.get("success", False))
        }
    
    def _generate_combined_insights(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate insights from multiple page analyses"""
        
        successful_results = [r for r in results.values() if r.get("success", False)]
        
        if not successful_results:
            return {"error": "No successful analyses to combine"}
        
        # Extract common patterns
        page_types = []
        all_fields = []
        complexities = []
        
        for result in successful_results:
            analysis = result.get("analysis", {})
            if "page_type" in analysis:
                page_types.append(analysis["page_type"])
            if "extractable_data" in analysis:
                primary_fields = analysis["extractable_data"].get("primary_fields", [])
                all_fields.extend(primary_fields)
            if "scraping_complexity" in analysis:
                complexities.append(analysis["scraping_complexity"])
        
        # Count occurrences
        from collections import Counter
        page_type_counts = Counter(page_types)
        field_counts = Counter(all_fields)
        complexity_counts = Counter(complexities)
        
        return {
            "common_page_types": dict(page_type_counts.most_common(3)),
            "most_common_fields": dict(field_counts.most_common(10)),
            "complexity_distribution": dict(complexity_counts),
            "total_unique_fields": len(set(all_fields)),
            "analysis_summary": f"Analyzed {len(successful_results)} pages successfully"
        }

# Convenience function for easy import
def analyze_webpage(url: str) -> Dict[str, Any]:
    """Quick function to analyze a single webpage"""
    analyzer = WebPageAnalyzer()
    return analyzer.analyze_page_structure(url)

def analyze_webpages(urls: List[str]) -> Dict[str, Any]:
    """Quick function to analyze multiple webpages"""
    analyzer = WebPageAnalyzer()
    return analyzer.analyze_multiple_urls(urls) 