#!/usr/bin/env python3
"""
Google Drive CLI Tool
Command-line interface for Google Drive operations
"""

import os
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm

from gdrive_manager import GoogleDriveManager


console = Console()


@click.group()
@click.option('--credentials', '-c', default='credentials.json', 
              help='Path to Google Drive credentials file')
@click.option('--token', '-t', default='token.json',
              help='Path to store authentication token')
@click.pass_context
def cli(ctx, credentials, token):
    """Google Drive CLI Tool with Live Progress Tracking"""
    ctx.ensure_object(dict)
    ctx.obj['manager'] = GoogleDriveManager(credentials, token)


@cli.command()
@click.pass_context
def auth(ctx):
    """Authenticate with Google Drive"""
    manager = ctx.obj['manager']
    
    console.print("🔐 Starting Google Drive authentication...", style="bold blue")
    
    if manager.authenticate():
        console.print("✅ Authentication successful!", style="bold green")
        
        # Show storage quota
        quota = manager.get_storage_quota()
        if quota:
            used_gb = quota['usage'] / (1024**3)
            limit_gb = quota['limit'] / (1024**3)
            percentage = (quota['usage'] / quota['limit']) * 100
            
            console.print(f"\n📊 Storage Usage: {used_gb:.2f} GB / {limit_gb:.2f} GB ({percentage:.1f}%)", 
                         style="cyan")
    else:
        console.print("❌ Authentication failed!", style="bold red")
        sys.exit(1)


@cli.command()
@click.option('--folder-id', '-f', help='Folder ID to list files from')
@click.option('--query', '-q', help='Search query (e.g., "name contains \'test\'")')
@click.option('--max-results', '-m', default=50, help='Maximum number of results')
@click.pass_context
def list(ctx, folder_id, query, max_results):
    """List files in Google Drive"""
    manager = ctx.obj['manager']
    
    if not manager.authenticate():
        return
    
    console.print("📂 Listing Google Drive files...", style="bold blue")
    
    files = manager.list_files(folder_id, query, max_results)
    manager.display_files_table(files)


@cli.command()
@click.argument('file_id')
@click.argument('output_path')
@click.option('--chunk-size', '-c', default=1048576, help='Download chunk size in bytes')
@click.pass_context
def download(ctx, file_id, output_path, chunk_size):
    """Download file from Google Drive
    
    FILE_ID: Google Drive file ID
    OUTPUT_PATH: Local path to save the file
    """
    manager = ctx.obj['manager']
    
    if not manager.authenticate():
        return
    
    console.print(f"⬇️  Starting download: {file_id}", style="bold blue")
    
    if manager.download_file(file_id, output_path, chunk_size):
        console.print("✅ Download completed successfully!", style="bold green")
    else:
        console.print("❌ Download failed!", style="bold red")
        sys.exit(1)


@cli.command()
@click.argument('file_path')
@click.option('--folder-id', '-f', help='Parent folder ID (optional)')
@click.option('--chunk-size', '-c', default=1048576, help='Upload chunk size in bytes')
@click.pass_context
def upload(ctx, file_path, folder_id, chunk_size):
    """Upload file to Google Drive
    
    FILE_PATH: Local file path to upload
    """
    manager = ctx.obj['manager']
    
    if not manager.authenticate():
        return
    
    console.print(f"⬆️  Starting upload: {file_path}", style="bold blue")
    
    file_id = manager.upload_file(file_path, folder_id, chunk_size)
    if file_id:
        console.print("✅ Upload completed successfully!", style="bold green")
        console.print(f"📄 File ID: {file_id}", style="cyan")
    else:
        console.print("❌ Upload failed!", style="bold red")
        sys.exit(1)


@cli.command()
@click.argument('folder_name')
@click.option('--parent-id', '-p', help='Parent folder ID (optional)')
@click.pass_context
def mkdir(ctx, folder_name, parent_id):
    """Create folder in Google Drive
    
    FOLDER_NAME: Name of the folder to create
    """
    manager = ctx.obj['manager']
    
    if not manager.authenticate():
        return
    
    console.print(f"📁 Creating folder: {folder_name}", style="bold blue")
    
    folder_id = manager.create_folder(folder_name, parent_id)
    if folder_id:
        console.print("✅ Folder created successfully!", style="bold green")
        console.print(f"📁 Folder ID: {folder_id}", style="cyan")
    else:
        console.print("❌ Failed to create folder!", style="bold red")
        sys.exit(1)


@cli.command()
@click.argument('file_id')
@click.option('--confirm', '-y', is_flag=True, help='Skip confirmation prompt')
@click.pass_context
def delete(ctx, file_id, confirm):
    """Delete file from Google Drive
    
    FILE_ID: Google Drive file ID to delete
    """
    manager = ctx.obj['manager']
    
    if not manager.authenticate():
        return
    
    # Get file info first
    file_info = manager.get_file_info(file_id)
    if not file_info:
        console.print("❌ File not found!", style="bold red")
        return
    
    file_name = file_info['name']
    
    if not confirm:
        if not Confirm.ask(f"Are you sure you want to delete '{file_name}'?"):
            console.print("❌ Deletion cancelled.", style="yellow")
            return
    
    console.print(f"🗑️  Deleting file: {file_name}", style="bold blue")
    
    if manager.delete_file(file_id):
        console.print("✅ File deleted successfully!", style="bold green")
    else:
        console.print("❌ Failed to delete file!", style="bold red")
        sys.exit(1)


@cli.command()
@click.argument('file_id')
@click.pass_context
def info(ctx, file_id):
    """Get detailed information about a file
    
    FILE_ID: Google Drive file ID
    """
    manager = ctx.obj['manager']
    
    if not manager.authenticate():
        return
    
    file_info = manager.get_file_info(file_id)
    if not file_info:
        console.print("❌ File not found!", style="bold red")
        return
    
    # Display file information
    table = Table(title=f"File Information: {file_info['name']}")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")
    
    for key, value in file_info.items():
        if key == 'size' and value:
            value = f"{int(value):,} bytes ({int(value)/(1024**2):.2f} MB)"
        table.add_row(key, str(value))
    
    console.print(table)


@cli.command()
@click.pass_context
def quota(ctx):
    """Show Google Drive storage quota"""
    manager = ctx.obj['manager']
    
    if not manager.authenticate():
        return
    
    quota = manager.get_storage_quota()
    if not quota:
        console.print("❌ Failed to get quota information!", style="bold red")
        return
    
    # Convert to human readable
    total_gb = quota['limit'] / (1024**3)
    used_gb = quota['usage'] / (1024**3)
    drive_gb = quota['usageInDrive'] / (1024**3)
    trash_gb = quota['usageInDriveTrash'] / (1024**3)
    free_gb = total_gb - used_gb
    percentage = (quota['usage'] / quota['limit']) * 100
    
    table = Table(title="Google Drive Storage Quota")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")
    table.add_column("Percentage", style="magenta")
    
    table.add_row("Total Storage", f"{total_gb:.2f} GB", "100.0%")
    table.add_row("Used Storage", f"{used_gb:.2f} GB", f"{percentage:.1f}%")
    table.add_row("Free Storage", f"{free_gb:.2f} GB", f"{100-percentage:.1f}%")
    table.add_row("Drive Files", f"{drive_gb:.2f} GB", f"{(drive_gb/total_gb)*100:.1f}%")
    table.add_row("Trash", f"{trash_gb:.2f} GB", f"{(trash_gb/total_gb)*100:.1f}%")
    
    console.print(table)


@cli.command()
@click.argument('source_path')
@click.argument('dest_folder_id')
@click.option('--recursive', '-r', is_flag=True, help='Upload folders recursively')
@click.option('--chunk-size', '-c', default=1048576, help='Upload chunk size in bytes')
@click.pass_context
def sync(ctx, source_path, dest_folder_id, recursive, chunk_size):
    """Sync local directory to Google Drive folder
    
    SOURCE_PATH: Local directory path
    DEST_FOLDER_ID: Google Drive destination folder ID
    """
    manager = ctx.obj['manager']
    
    if not manager.authenticate():
        return
    
    source_path = Path(source_path)
    if not source_path.exists():
        console.print(f"❌ Source path not found: {source_path}", style="bold red")
        return
    
    console.print(f"🔄 Syncing {source_path} to Google Drive...", style="bold blue")
    
    if source_path.is_file():
        # Upload single file
        file_id = manager.upload_file(str(source_path), dest_folder_id, chunk_size)
        if file_id:
            console.print("✅ Sync completed successfully!", style="bold green")
        else:
            console.print("❌ Sync failed!", style="bold red")
    elif source_path.is_dir():
        if not recursive:
            console.print("❌ Use --recursive flag to sync directories", style="bold red")
            return
        
        # Upload directory recursively
        uploaded_count = 0
        failed_count = 0
        
        for file_path in source_path.rglob('*'):
            if file_path.is_file():
                relative_path = file_path.relative_to(source_path)
                console.print(f"📄 Uploading: {relative_path}", style="blue")
                
                file_id = manager.upload_file(str(file_path), dest_folder_id, chunk_size)
                if file_id:
                    uploaded_count += 1
                else:
                    failed_count += 1
        
        console.print(f"✅ Sync completed: {uploaded_count} uploaded, {failed_count} failed", 
                     style="bold green")


if __name__ == '__main__':
    cli() 