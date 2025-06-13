#!/usr/bin/env python3
"""
Configuration settings for Google Drive operations
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# File paths
CREDENTIALS_FILE = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
TOKEN_FILE = os.getenv('GOOGLE_TOKEN_FILE', 'token.json')

# Upload/Download settings
DEFAULT_CHUNK_SIZE = int(os.getenv('DEFAULT_CHUNK_SIZE', 1024 * 1024))  # 1MB
MAX_WORKERS = int(os.getenv('MAX_WORKERS', 4))

# Progress display settings
PROGRESS_UPDATE_INTERVAL = float(os.getenv('PROGRESS_UPDATE_INTERVAL', 0.1))
SHOW_TRANSFER_SPEED = os.getenv('SHOW_TRANSFER_SPEED', 'true').lower() == 'true'
SHOW_ETA = os.getenv('SHOW_ETA', 'true').lower() == 'true'

# Logging configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'gdrive_operations.log')

# Google Drive API settings
SCOPES = ['https://www.googleapis.com/auth/drive']

# Default directories
DOWNLOADS_DIR = Path('downloads')
UPLOADS_DIR = Path('uploads')

# Ensure directories exist
DOWNLOADS_DIR.mkdir(exist_ok=True)
UPLOADS_DIR.mkdir(exist_ok=True)

# File type mappings for better organization
FILE_TYPE_FOLDERS = {
    'images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'],
    'videos': ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'],
    'documents': ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt'],
    'spreadsheets': ['.xls', '.xlsx', '.csv', '.ods'],
    'presentations': ['.ppt', '.pptx', '.odp'],
    'archives': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'],
    'code': ['.py', '.js', '.html', '.css', '.cpp', '.java', '.go', '.rs']
} 