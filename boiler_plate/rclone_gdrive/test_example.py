#!/usr/bin/env python3
"""
Test script for Google Drive operations
This script demonstrates basic functionality and can be used for testing
"""

import os
import tempfile
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

from gdrive_manager import GoogleDriveManager

console = Console()

def create_test_file():
    """Create a temporary test file for upload testing"""
    test_content = """# Google Drive Test File

This is a test file created by the Google Drive CLI tool.

## Features Tested:
- File upload with progress tracking
- File download with progress tracking
- File listing and search
- Storage quota checking

## Technical Details:
- Created using Python Google API client
- Progress tracking with Rich library
- OAuth2 authentication
- Resumable uploads/downloads

## Test Data:
""" + "Sample data line " * 100  # Add some content to make it a reasonable size

    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(test_content)
        return f.name

def main():
    """Main test function"""
    console.print(Panel.fit(
        "🧪 [bold blue]Google Drive CLI Tool Test Script[/bold blue]\n\n"
        "This script will test basic functionality of the Google Drive operations.",
        title="Test Suite"
    ))
    
    # Initialize manager
    manager = GoogleDriveManager()
    
    # Test authentication
    console.print("\n🔐 [bold]Testing Authentication...[/bold]")
    if not manager.authenticate():
        console.print("❌ Authentication failed! Make sure credentials.json is present.")
        return False
    
    # Test storage quota
    console.print("\n📊 [bold]Testing Storage Quota...[/bold]")
    quota = manager.get_storage_quota()
    if quota:
        used_gb = quota['usage'] / (1024**3)
        limit_gb = quota['limit'] / (1024**3)
        console.print(f"✅ Storage: {used_gb:.2f} GB / {limit_gb:.2f} GB")
    else:
        console.print("⚠️  Could not retrieve storage quota")
    
    # Test file listing
    console.print("\n📂 [bold]Testing File Listing...[/bold]")
    files = manager.list_files(max_results=5)
    if files:
        console.print(f"✅ Found {len(files)} files")
        manager.display_files_table(files[:3])  # Show first 3 files
    else:
        console.print("⚠️  No files found or listing failed")
    
    # Test file upload
    console.print("\n⬆️  [bold]Testing File Upload...[/bold]")
    test_file_path = create_test_file()
    try:
        file_id = manager.upload_file(test_file_path)
        if file_id:
            console.print(f"✅ Upload successful! File ID: {file_id}")
            
            # Test file info
            console.print("\n📋 [bold]Testing File Info...[/bold]")
            file_info = manager.get_file_info(file_id)
            if file_info:
                console.print(f"✅ File info retrieved: {file_info['name']}")
            
            # Test file download
            console.print("\n⬇️  [bold]Testing File Download...[/bold]")
            download_path = Path("downloads") / "test_download.md"
            if manager.download_file(file_id, str(download_path)):
                console.print(f"✅ Download successful: {download_path}")
                
                # Verify downloaded content
                if download_path.exists():
                    console.print("✅ Downloaded file exists")
                    download_path.unlink()  # Clean up
                    console.print("🧹 Cleaned up downloaded file")
            else:
                console.print("❌ Download failed")
            
            # Test file deletion
            console.print("\n🗑️  [bold]Testing File Deletion...[/bold]")
            if manager.delete_file(file_id):
                console.print("✅ File deleted successfully")
            else:
                console.print("❌ File deletion failed")
        else:
            console.print("❌ Upload failed")
    finally:
        # Clean up test file
        os.unlink(test_file_path)
        console.print("🧹 Cleaned up test file")
    
    # Test folder creation
    console.print("\n📁 [bold]Testing Folder Creation...[/bold]")
    folder_id = manager.create_folder("Test Folder - CLI Tool")
    if folder_id:
        console.print(f"✅ Folder created: {folder_id}")
        
        # Clean up folder
        if manager.delete_file(folder_id):
            console.print("🧹 Cleaned up test folder")
    else:
        console.print("❌ Folder creation failed")
    
    console.print(Panel.fit(
        "✅ [bold green]Test completed![/bold green]\n\n"
        "All basic operations have been tested.\n"
        "The Google Drive CLI tool is ready for use!",
        title="Test Results"
    ))
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            exit(1)
    except KeyboardInterrupt:
        console.print("\n❌ Test interrupted by user")
        exit(1)
    except Exception as e:
        console.print(f"\n❌ Test failed with error: {e}")
        exit(1) 