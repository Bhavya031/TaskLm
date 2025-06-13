# Firecrawl Basic Boilerplate

A simple boilerplate for web scraping using Firecrawl API.

## Setup

1. Initialize the project with uv:
```bash
uv init
```

2. Install dependencies:
```bash
uv add firecrawl-py python-dotenv
```

3. Create a `.env` file in the project root and add your Firecrawl API key:
```
FIRECRAWL_API_KEY=fc-YOUR_API_KEY
```

## Usage

Run the example script:
```bash
uv run python firecrawl_example.py
```

The script will scrape the Firecrawl website and print the results.

## Basic Function

The boilerplate includes a basic scraping function:

```python
def basic_scrape(url: str):
    """
    Basic function to scrape a website
    """
    try:
        # Scrape the website
        scrape_result = app.scrape_url(url, formats=['markdown', 'html'])
        print("\nScrape Result:")
        print("=" * 50)
        print(scrape_result)
        return scrape_result
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return None
```

## Documentation

For more information about Firecrawl's capabilities, visit the [Firecrawl Documentation](https://docs.firecrawl.dev/).
