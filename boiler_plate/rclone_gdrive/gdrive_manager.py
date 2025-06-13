#!/usr/bin/env python3
"""
Google Drive Manager with Live Progress Tracking
Boilerplate code for Google Drive operations using Google API
"""

import os
import io
import json
import time
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from threading import Event, Thread

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from rich.console import Console
from rich.progress import (
    Progress,
    TaskID,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TimeRemainingColumn,
    FileSizeColumn,
    TransferSpeedColumn,
    DownloadColumn,
)
from rich.table import Table
from rich.live import Live
import click


# Google Drive API scopes
SCOPES = ['https://www.googleapis.com/auth/drive']


class GDriveProgressCallback:
    """Progress callback for Google Drive operations"""
    
    def __init__(self, progress: Progress, task_id: TaskID, total_size: int):
        self.progress = progress
        self.task_id = task_id
        self.total_size = total_size
        self.transferred = 0
        
    def update(self, chunk_size: int):
        """Update progress with transferred bytes"""
        self.transferred += chunk_size
        self.progress.update(
            self.task_id,
            completed=self.transferred,
            total=self.total_size
        )


class GoogleDriveManager:
    """Google Drive Manager with authentication and file operations"""
    
    def __init__(self, credentials_file: str = "credentials.json", token_file: str = "token.json"):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        self.console = Console()
        self.authenticated = False
        
    def authenticate(self) -> bool:
        """Authenticate with Google Drive API"""
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_file):
            try:
                creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
                self.console.print("✅ Loaded existing credentials", style="green")
            except Exception as e:
                self.console.print(f"❌ Error loading token: {e}", style="red")
        
        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    self.console.print("✅ Refreshed credentials", style="green")
                except Exception as e:
                    self.console.print(f"❌ Error refreshing token: {e}", style="red")
                    creds = None
            
            if not creds:
                if not os.path.exists(self.credentials_file):
                    self.console.print(f"❌ Credentials file '{self.credentials_file}' not found!", style="red")
                    self.console.print("\n📋 To set up Google Drive API credentials:", style="yellow")
                    self.console.print("1. Go to https://console.cloud.google.com/", style="cyan")
                    self.console.print("2. Create or select a project", style="cyan")
                    self.console.print("3. Enable Google Drive API", style="cyan")
                    self.console.print("4. Create OAuth 2.0 credentials", style="cyan")
                    self.console.print("5. Download credentials.json file", style="cyan")
                    return False
                
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                    self.console.print("✅ New credentials obtained", style="green")
                except Exception as e:
                    self.console.print(f"❌ Authentication failed: {e}", style="red")
                    return False
            
            # Save credentials
            try:
                with open(self.token_file, 'w') as token:
                    token.write(creds.to_json())
                self.console.print(f"✅ Credentials saved to {self.token_file}", style="green")
            except Exception as e:
                self.console.print(f"❌ Error saving token: {e}", style="red")
        
        # Build service
        try:
            self.service = build('drive', 'v3', credentials=creds)
            self.authenticated = True
            self.console.print("✅ Google Drive service initialized", style="green")
            return True
        except Exception as e:
            self.console.print(f"❌ Failed to build service: {e}", style="red")
            return False
    
    def get_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get file information from Google Drive"""
        try:
            file_info = self.service.files().get(
                fileId=file_id, 
                fields='id,name,size,mimeType,parents,createdTime,modifiedTime'
            ).execute()
            return file_info
        except HttpError as e:
            self.console.print(f"❌ Error getting file info: {e}", style="red")
            return None
    
    def list_files(self, folder_id: str = None, query: str = None, max_results: int = 100) -> List[Dict[str, Any]]:
        """List files in Google Drive"""
        try:
            # Build query
            search_query = []
            if folder_id:
                search_query.append(f"'{folder_id}' in parents")
            if query:
                search_query.append(query)
            
            query_string = " and ".join(search_query) if search_query else None
            
            results = self.service.files().list(
                q=query_string,
                pageSize=max_results,
                fields="nextPageToken, files(id,name,size,mimeType,parents,createdTime,modifiedTime)"
            ).execute()
            
            return results.get('files', [])
        except HttpError as e:
            self.console.print(f"❌ Error listing files: {e}", style="red")
            return []
    
    def download_file(self, file_id: str, output_path: str, chunk_size: int = 1024*1024) -> bool:
        """Download file from Google Drive with progress tracking"""
        if not self.authenticated:
            self.console.print("❌ Not authenticated", style="red")
            return False
        
        try:
            # Get file info
            file_info = self.get_file_info(file_id)
            if not file_info:
                return False
            
            file_name = file_info['name']
            file_size = int(file_info.get('size', 0))
            
            # Create output directory
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Set up progress tracking
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.fields[filename]}", justify="right"),
                BarColumn(bar_width=None),
                "[progress.percentage]{task.percentage:>3.1f}%",
                "•",
                DownloadColumn(),
                "•",
                TransferSpeedColumn(),
                "•",
                TimeRemainingColumn(),
                console=self.console,
                transient=True,
            ) as progress:
                
                task_id = progress.add_task(
                    "download",
                    filename=file_name,
                    total=file_size
                )
                
                # Download file
                request = self.service.files().get_media(fileId=file_id)
                with open(output_path, 'wb') as fh:
                    downloader = MediaIoBaseDownload(fh, request, chunksize=chunk_size)
                    
                    done = False
                    while done is False:
                        status, done = downloader.next_chunk()
                        if status:
                            progress.update(
                                task_id,
                                completed=int(status.resumable_progress)
                            )
            
            self.console.print(f"✅ Downloaded: {file_name} → {output_path}", style="green")
            return True
            
        except HttpError as e:
            self.console.print(f"❌ Download failed: {e}", style="red")
            return False
        except Exception as e:
            self.console.print(f"❌ Unexpected error: {e}", style="red")
            return False
    
    def upload_file(self, file_path: str, parent_folder_id: str = None, 
                   chunk_size: int = 1024*1024) -> Optional[str]:
        """Upload file to Google Drive with progress tracking"""
        if not self.authenticated:
            self.console.print("❌ Not authenticated", style="red")
            return None
        
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                self.console.print(f"❌ File not found: {file_path}", style="red")
                return None
            
            file_size = file_path.stat().st_size
            file_name = file_path.name
            
            # File metadata
            file_metadata = {'name': file_name}
            if parent_folder_id:
                file_metadata['parents'] = [parent_folder_id]
            
            # Set up progress tracking
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.fields[filename]}", justify="right"),
                BarColumn(bar_width=None),
                "[progress.percentage]{task.percentage:>3.1f}%",
                "•",
                FileSizeColumn(),
                "•",
                TransferSpeedColumn(),
                "•",
                TimeRemainingColumn(),
                console=self.console,
                transient=True,
            ) as progress:
                
                task_id = progress.add_task(
                    "upload",
                    filename=file_name,
                    total=file_size
                )
                
                # Upload file
                media = MediaFileUpload(
                    str(file_path),
                    chunksize=chunk_size,
                    resumable=True
                )
                
                request = self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                )
                
                response = None
                while response is None:
                    status, response = request.next_chunk()
                    if status:
                        progress.update(
                            task_id,
                            completed=int(status.resumable_progress)
                        )
            
            file_id = response.get('id')
            self.console.print(f"✅ Uploaded: {file_name} (ID: {file_id})", style="green")
            return file_id
            
        except HttpError as e:
            self.console.print(f"❌ Upload failed: {e}", style="red")
            return None
        except Exception as e:
            self.console.print(f"❌ Unexpected error: {e}", style="red")
            return None
    
    def create_folder(self, folder_name: str, parent_folder_id: str = None) -> Optional[str]:
        """Create folder in Google Drive"""
        if not self.authenticated:
            self.console.print("❌ Not authenticated", style="red")
            return None
        
        try:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_folder_id:
                file_metadata['parents'] = [parent_folder_id]
            
            folder = self.service.files().create(
                body=file_metadata,
                fields='id'
            ).execute()
            
            folder_id = folder.get('id')
            self.console.print(f"✅ Created folder: {folder_name} (ID: {folder_id})", style="green")
            return folder_id
            
        except HttpError as e:
            self.console.print(f"❌ Failed to create folder: {e}", style="red")
            return None
    
    def delete_file(self, file_id: str) -> bool:
        """Delete file from Google Drive"""
        if not self.authenticated:
            self.console.print("❌ Not authenticated", style="red")
            return False
        
        try:
            self.service.files().delete(fileId=file_id).execute()
            self.console.print(f"✅ Deleted file: {file_id}", style="green")
            return True
        except HttpError as e:
            self.console.print(f"❌ Failed to delete file: {e}", style="red")
            return False
    
    def get_storage_quota(self) -> Dict[str, int]:
        """Get Google Drive storage quota information"""
        if not self.authenticated:
            self.console.print("❌ Not authenticated", style="red")
            return {}
        
        try:
            about = self.service.about().get(fields='storageQuota').execute()
            quota = about.get('storageQuota', {})
            
            return {
                'limit': int(quota.get('limit', 0)),
                'usage': int(quota.get('usage', 0)),
                'usageInDrive': int(quota.get('usageInDrive', 0)),
                'usageInDriveTrash': int(quota.get('usageInDriveTrash', 0))
            }
        except HttpError as e:
            self.console.print(f"❌ Failed to get quota: {e}", style="red")
            return {}
    
    def display_files_table(self, files: List[Dict[str, Any]]):
        """Display files in a formatted table"""
        if not files:
            self.console.print("No files found.", style="yellow")
            return
        
        table = Table(title="Google Drive Files")
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Size", style="magenta")
        table.add_column("Type", style="green")
        table.add_column("Modified", style="blue")
        table.add_column("ID", style="dim")
        
        for file in files:
            size = file.get('size', 'N/A')
            if size != 'N/A':
                size = f"{int(size):,} bytes"
            
            modified = file.get('modifiedTime', 'N/A')
            if modified != 'N/A':
                modified = modified.split('T')[0]  # Just the date
            
            table.add_row(
                file['name'],
                size,
                file.get('mimeType', 'Unknown'),
                modified,
                file['id'][:20] + "..."
            )
        
        self.console.print(table) 