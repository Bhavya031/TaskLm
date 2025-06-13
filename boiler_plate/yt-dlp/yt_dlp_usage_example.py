#!/usr/bin/env python3
"""
Usage example for the YouTube Downloader Boilerplate
Demonstrates all key features
"""

from ytdlp_downloader import YouTubeDownloader, test_downloader

def main():
    print("🚀 YouTube Downloader Boilerplate - Usage Examples")
    print("=" * 55)
    
    # Example 1: Test functionality
    print("\n1️⃣ Testing URL normalization and info extraction:")
    test_downloader()
    
    # Example 2: Create downloader instance
    print("\n2️⃣ Creating downloader instance:")
    downloader = YouTubeDownloader("example_downloads")
    print("✅ Downloader created with download directory: example_downloads/")
    
    # Example 3: URL normalization demo
    print("\n3️⃣ URL Normalization Examples:")
    test_urls = [
        "https://youtu.be/CdqEe3k1ohc",
        "youtu.be/CdqEe3k1ohc",
        "https://www.youtube.com/watch?v=CdqEe3k1ohc",
        "youtube.com/watch?v=CdqEe3k1ohc"
    ]
    
    for url in test_urls:
        normalized = downloader.normalize_url(url)
        print(f"   📝 {url}")
        print(f"   ➡️  {normalized}")
    
    # Example 4: Get video info and qualities
    print("\n4️⃣ Video Information and Quality Options:")
    url = "https://youtu.be/CdqEe3k1ohc"
    
    try:
        info = downloader.get_video_info(url)
        qualities = downloader.get_available_qualities(url)
        
        print(f"   🎥 Title: {info.get('title', 'N/A')}")
        print(f"   👤 Uploader: {info.get('uploader', 'N/A')}")
        print(f"   ⏱️  Duration: {info.get('duration', 'N/A')} seconds")
        print(f"   👁️  View Count: {info.get('view_count', 'N/A'):,}")
        
        downloader.display_qualities(qualities, info.get('title', 'Unknown'))
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Example 5: Batch download demo (info only, no actual download)
    print("\n5️⃣ Batch Download Example (Info Only):")
    batch_urls = [
        "https://youtu.be/CdqEe3k1ohc",
        "https://www.youtube.com/watch?v=CdqEe3k1ohc"  # Same video, different format
    ]
    
    print(f"   📚 Would process {len(batch_urls)} URLs:")
    for i, url in enumerate(batch_urls, 1):
        normalized = downloader.normalize_url(url)
        print(f"   {i}. {url} → {normalized}")
    
    print("\n6️⃣ Interactive Download Options:")
    print("   To actually download videos, run:")
    print("   📥 python3 ytdlp_downloader.py")
    print("   📥 Or use: downloader.download_video('URL') in your code")
    
    print("\n✨ Features Summary:")
    print("   ✅ Supports youtube.com/watch?v= and youtu.be/ URLs")
    print("   ✅ Custom progress bar with tqdm (not default yt-dlp)")
    print("   ✅ Quality selection with detailed format information")
    print("   ✅ Batch downloading with progress tracking")
    print("   ✅ Error handling and user-friendly messages")
    print("   ✅ Audio-only download option")

if __name__ == "__main__":
    main() 