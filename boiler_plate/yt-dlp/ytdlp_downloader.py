#!/usr/bin/env python3
"""
YouTube Downloader Boilerplate using yt-dlp
Supports both youtube.com/watch?v= and youtu.be/ URLs
Features: Quality selection, Custom progress bar, Download tracking
"""

import os
import sys
import re
import json
import time
from typing import Dict, List, Optional, Any
from pathlib import Path

try:
    import yt_dlp
    from tqdm import tqdm
except ImportError:
    print("Required packages not found. Please install:")
    print("pip install yt-dlp tqdm")
    sys.exit(1)


class YouTubeDownloader:
    def __init__(self, download_dir: str = "downloads"):
        """
        Initialize the YouTube downloader
        
        Args:
            download_dir: Directory to save downloaded videos
        """
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        self.progress_bar = None
        self.current_filename = ""
        
    def normalize_url(self, url: str) -> str:
        """
        Normalize YouTube URLs to standard format
        Supports both youtube.com/watch?v= and youtu.be/ formats
        
        Args:
            url: YouTube URL in any format
            
        Returns:
            Normalized YouTube URL
        """
        # Remove any whitespace
        url = url.strip()
        
        # Pattern for youtu.be/ format
        youtu_be_pattern = r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]+)'
        match = re.search(youtu_be_pattern, url)
        if match:
            video_id = match.group(1)
            return f"https://www.youtube.com/watch?v={video_id}"
        
        # Pattern for youtube.com/watch format
        youtube_pattern = r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)'
        match = re.search(youtube_pattern, url)
        if match:
            return url if url.startswith('http') else f"https://{url}"
        
        # If no match, assume it's already in correct format or invalid
        return url
    
    def get_video_info(self, url: str) -> Dict[str, Any]:
        """
        Get video information including available qualities
        
        Args:
            url: YouTube video URL
            
        Returns:
            Dictionary containing video information
        """
        normalized_url = self.normalize_url(url)
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(normalized_url, download=False)
                return info
        except Exception as e:
            raise Exception(f"Failed to get video info: {str(e)}")
    
    def get_available_qualities(self, url: str) -> List[Dict[str, Any]]:
        """
        Get all available video qualities
        
        Args:
            url: YouTube video URL
            
        Returns:
            List of available quality options
        """
        info = self.get_video_info(url)
        formats = info.get('formats', [])
        
        # Filter for video formats with both video and audio or video-only
        video_formats = []
        audio_formats = []
        
        for fmt in formats:
            if fmt.get('vcodec') != 'none':  # Has video
                video_formats.append(fmt)
            elif fmt.get('acodec') != 'none':  # Audio only
                audio_formats.append(fmt)
        
        # Group by quality
        quality_map = {}
        
        for fmt in video_formats:
            height = fmt.get('height')
            if height:
                quality_key = f"{height}p"
                if quality_key not in quality_map:
                    quality_map[quality_key] = {
                        'height': height,
                        'formats': []
                    }
                quality_map[quality_key]['formats'].append(fmt)
        
        # Sort by quality (highest first)
        sorted_qualities = sorted(
            quality_map.items(), 
            key=lambda x: x[1]['height'], 
            reverse=True
        )
        
        return sorted_qualities
    
    def display_qualities(self, qualities: List[Dict[str, Any]], video_title: str) -> None:
        """
        Display available qualities to user
        
        Args:
            qualities: List of quality options
            video_title: Title of the video
        """
        print(f"\n🎥 Video: {video_title}")
        print("=" * 60)
        print("Available Qualities:")
        print("-" * 30)
        
        for i, (quality_name, quality_info) in enumerate(qualities, 1):
            formats = quality_info['formats']
            best_format = max(formats, key=lambda x: x.get('tbr', 0) or 0)
            
            file_size = best_format.get('filesize') or best_format.get('filesize_approx')
            size_str = f" (~{file_size // (1024*1024):.1f} MB)" if file_size else ""
            
            fps = best_format.get('fps', 'N/A')
            vcodec = best_format.get('vcodec', 'N/A')
            
            print(f"{i:2d}. {quality_name} - {fps}fps - {vcodec}{size_str}")
        
        print(f"{len(qualities) + 1:2d}. Audio Only (Best Quality)")
        print("-" * 30)
    
    def progress_hook(self, d: Dict[str, Any]) -> None:
        """
        Custom progress hook for yt-dlp downloads
        
        Args:
            d: Download progress dictionary
        """
        if d['status'] == 'downloading':
            if not self.progress_bar:
                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
                if total_bytes:
                    self.progress_bar = tqdm(
                        total=total_bytes,
                        unit='B',
                        unit_scale=True,
                        desc=f"📥 {self.current_filename}"
                    )
            
            if self.progress_bar:
                downloaded = d.get('downloaded_bytes', 0)
                self.progress_bar.n = downloaded
                self.progress_bar.refresh()
                
        elif d['status'] == 'finished':
            if self.progress_bar:
                self.progress_bar.close()
                self.progress_bar = None
            print(f"\n✅ Downloaded: {d['filename']}")
            
        elif d['status'] == 'error':
            if self.progress_bar:
                self.progress_bar.close()
                self.progress_bar = None
            print(f"\n❌ Error downloading: {d.get('filename', 'Unknown')}")
    
    def download_video(self, url: str, quality_choice: int = None) -> bool:
        """
        Download video with selected quality
        
        Args:
            url: YouTube video URL
            quality_choice: Selected quality index (None for interactive selection)
            
        Returns:
            True if download successful, False otherwise
        """
        try:
            normalized_url = self.normalize_url(url)
            info = self.get_video_info(normalized_url)
            video_title = info.get('title', 'Unknown Video')
            
            # Sanitize filename
            safe_title = re.sub(r'[<>:"/\\|?*]', '_', video_title)
            self.current_filename = safe_title[:50] + "..." if len(safe_title) > 50 else safe_title
            
            qualities = self.get_available_qualities(normalized_url)
            
            if quality_choice is None:
                self.display_qualities(qualities, video_title)
                
                while True:
                    try:
                        choice = int(input(f"\nSelect quality (1-{len(qualities) + 1}): "))
                        if 1 <= choice <= len(qualities) + 1:
                            quality_choice = choice
                            break
                        else:
                            print("Invalid choice. Please try again.")
                    except ValueError:
                        print("Please enter a valid number.")
            
            # Configure download options
            ydl_opts = {
                'outtmpl': str(self.download_dir / '%(title)s.%(ext)s'),
                'progress_hooks': [self.progress_hook],
            }
            
            if quality_choice <= len(qualities):
                # Video download
                selected_quality = qualities[quality_choice - 1]
                quality_name = selected_quality[0]
                
                print(f"\n🎯 Selected: {quality_name}")
                
                # Use best format for selected quality
                ydl_opts['format'] = f"best[height<={selected_quality[1]['height']}]"
                
            else:
                # Audio only download
                print(f"\n🎯 Selected: Audio Only")
                ydl_opts['format'] = 'bestaudio/best'
                ydl_opts['outtmpl'] = str(self.download_dir / '%(title)s.%(ext)s')
            
            print(f"📁 Download directory: {self.download_dir.absolute()}")
            print("🚀 Starting download...\n")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([normalized_url])
            
            return True
            
        except Exception as e:
            print(f"❌ Download failed: {str(e)}")
            return False
    
    def batch_download(self, urls: List[str], quality_choice: int = None) -> Dict[str, bool]:
        """
        Download multiple videos
        
        Args:
            urls: List of YouTube URLs
            quality_choice: Quality choice for all videos (None for interactive)
            
        Returns:
            Dictionary mapping URLs to success status
        """
        results = {}
        
        print(f"📚 Batch downloading {len(urls)} video(s)...")
        
        for i, url in enumerate(urls, 1):
            print(f"\n{'='*60}")
            print(f"📹 Processing video {i}/{len(urls)}")
            print(f"🔗 URL: {url}")
            
            results[url] = self.download_video(url, quality_choice)
            
            if i < len(urls):
                print("\n⏸️  Waiting 2 seconds before next download...")
                time.sleep(2)
        
        return results


def test_downloader():
    """
    Test function to verify the downloader works
    """
    print("🧪 Testing YouTube Downloader...")
    
    # Test URLs - both formats
    test_urls = [
        "https://youtu.be/CdqEe3k1ohc",  # youtu.be format
        "https://www.youtube.com/watch?v=CdqEe3k1ohc"  # youtube.com format
    ]
    
    downloader = YouTubeDownloader("test_downloads")
    
    for url in test_urls:
        print(f"\n🔍 Testing URL: {url}")
        normalized = downloader.normalize_url(url)
        print(f"✅ Normalized: {normalized}")
        
        try:
            info = downloader.get_video_info(url)
            print(f"📹 Title: {info.get('title', 'N/A')}")
            print(f"⏱️  Duration: {info.get('duration', 'N/A')} seconds")
            
            qualities = downloader.get_available_qualities(url)
            print(f"🎯 Available qualities: {len(qualities)}")
            
            print("✅ Test passed!")
            
        except Exception as e:
            print(f"❌ Test failed: {str(e)}")
    
    print("\n🎉 Testing complete!")


def main():
    """
    Main function - Interactive YouTube downloader
    """
    print("🚀 YouTube Downloader Boilerplate")
    print("=" * 40)
    
    downloader = YouTubeDownloader()
    
    while True:
        print("\nOptions:")
        print("1. Download single video")
        print("2. Download multiple videos")
        print("3. Test downloader")
        print("4. Exit")
        
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == "1":
            url = input("\nEnter YouTube URL: ").strip()
            if url:
                downloader.download_video(url)
            else:
                print("❌ Invalid URL")
                
        elif choice == "2":
            print("\nEnter YouTube URLs (one per line, empty line to finish):")
            urls = []
            while True:
                url = input().strip()
                if not url:
                    break
                urls.append(url)
            
            if urls:
                results = downloader.batch_download(urls)
                
                print(f"\n📊 Batch Download Results:")
                print("-" * 30)
                successful = sum(results.values())
                print(f"✅ Successful: {successful}/{len(urls)}")
                
                for url, success in results.items():
                    status = "✅" if success else "❌"
                    print(f"{status} {url}")
            else:
                print("❌ No URLs provided")
                
        elif choice == "3":
            test_downloader()
            
        elif choice == "4":
            print("👋 Goodbye!")
            break
            
        else:
            print("❌ Invalid choice")


if __name__ == "__main__":
    main() 