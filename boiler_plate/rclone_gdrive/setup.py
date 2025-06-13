#!/usr/bin/env python3
"""
Setup script for Google Drive CLI tool
This script helps users get started quickly
"""

import os
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

console = Console()

def check_credentials():
    """Check if credentials.json exists"""
    creds_file = Path("credentials.json")
    if creds_file.exists():
        console.print("✅ Found credentials.json", style="green")
        return True
    else:
        console.print("❌ credentials.json not found", style="red")
        return False

def show_setup_instructions():
    """Show setup instructions for Google Cloud"""
    instructions = """
🔧 [bold blue]Google Cloud Setup Required[/bold blue]

To use this tool, you need to set up Google Drive API access:

[bold yellow]1. Go to Google Cloud Console[/bold yellow]
   https://console.cloud.google.com/

[bold yellow]2. Create or select a project[/bold yellow]

[bold yellow]3. Enable Google Drive API[/bold yellow]
   - Go to "APIs & Services" > "Library"
   - Search for "Google Drive API"
   - Click "Enable"

[bold yellow]4. Create OAuth 2.0 Credentials[/bold yellow]
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth 2.0 Client IDs"
   - Choose "Desktop application"
   - Download as credentials.json

[bold yellow]5. Place credentials.json in this directory[/bold yellow]
   {current_dir}

[bold red]Important:[/bold red] Never commit credentials.json to version control!
""".format(current_dir=Path.cwd())
    
    console.print(Panel(instructions, title="Setup Instructions"))

def main():
    """Main setup function"""
    console.print(Panel.fit(
        "🚀 [bold blue]Google Drive CLI Tool Setup[/bold blue]\n\n"
        "This script will help you set up the Google Drive CLI tool.",
        title="Welcome"
    ))
    
    # Check if credentials exist
    if check_credentials():
        console.print("\n🎉 [bold green]You're all set![/bold green]")
        console.print("\nNext steps:")
        console.print("1. Run authentication: [cyan]uv run python main.py auth[/cyan]")
        console.print("2. List your files: [cyan]uv run python main.py list[/cyan]")
        console.print("3. Check storage quota: [cyan]uv run python main.py quota[/cyan]")
        console.print("4. Upload a file: [cyan]uv run python main.py upload /path/to/file[/cyan]")
        
        if Confirm.ask("\nWould you like to run the test script?"):
            console.print("\n🧪 Running test script...")
            os.system("uv run python test_example.py")
        
    else:
        show_setup_instructions()
        
        console.print("\n📋 [bold]Setup Checklist:[/bold]")
        console.print("❌ Google Cloud project created")
        console.print("❌ Google Drive API enabled")
        console.print("❌ OAuth 2.0 credentials created")
        console.print("❌ credentials.json downloaded")
        console.print("❌ credentials.json placed in project directory")
        
        console.print("\n💡 [bold yellow]After completing the setup:[/bold yellow]")
        console.print("1. Place credentials.json in this directory")
        console.print("2. Run this setup script again")
        console.print("3. Or directly run: [cyan]uv run python main.py auth[/cyan]")

if __name__ == "__main__":
    main() 