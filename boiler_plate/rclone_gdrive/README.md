# Google Drive CLI Tool

A powerful command-line tool for Google Drive operations with live progress tracking and beautiful output.

## Features

- ✅ **OAuth2 Authentication** - Secure login to your Google account
- 📊 **Live Progress Tracking** - Real-time upload/download progress with speed and ETA
- 🎨 **Beautiful CLI Interface** - Rich formatted output with colors and tables
- 📁 **File Management** - Upload, download, list, create folders, and delete files
- 🔄 **Sync Operations** - Sync local directories to Google Drive
- 📈 **Storage Quota Display** - View your Google Drive storage usage
- 🔍 **File Search** - Search files with queries
- 📋 **Detailed File Info** - Get comprehensive file information

## Prerequisites

1. **Python 3.13+** with uv package manager
2. **Google Cloud Project** with Drive API enabled
3. **OAuth2 Credentials** from Google Cloud Console

## Setup Instructions

### 1. Google Cloud Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the Google Drive API:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Google Drive API" and enable it
4. Create OAuth2 credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth 2.0 Client IDs"
   - Choose "Desktop application"
   - Download the credentials as `credentials.json`

### 2. Project Setup

```bash
# Navigate to the project directory
cd boiler_plate/rclone_gdrive

# Install dependencies (already done if you followed setup)
uv add google-api-python-client google-auth-httplib2 google-auth-oauthlib tqdm rich click python-dotenv

# Place your credentials.json file in this directory
cp /path/to/your/credentials.json .

# Authenticate with Google Drive
uv run python main.py auth
```

## Usage Examples

### Authentication
```bash
# First-time authentication
uv run python main.py auth
```

### File Operations

#### List Files
```bash
# List all files
uv run python main.py list

# List files in specific folder
uv run python main.py list --folder-id "1AbC2DeF3GhI4JkL5MnO6PqR7StU8VwX9Yz"

# Search for files
uv run python main.py list --query "name contains 'document'"

# Limit results
uv run python main.py list --max-results 10
```

#### Upload Files
```bash
# Upload single file
uv run python main.py upload "./document.pdf"

# Upload to specific folder
uv run python main.py upload "./document.pdf" --folder-id "1AbC2DeF3GhI4JkL5MnO6PqR7StU8VwX9Yz"

# Upload with custom chunk size (for large files)
uv run python main.py upload "./large_video.mp4" --chunk-size 2097152  # 2MB chunks
```

#### Download Files
```bash
# Download file by ID
uv run python main.py download "1AbC2DeF3GhI4JkL5MnO6PqR7StU8VwX9Yz" "./downloads/file.pdf"

# Download with custom chunk size
uv run python main.py download "1AbC2DeF3GhI4JkL5MnO6PqR7StU8VwX9Yz" "./downloads/file.pdf" --chunk-size 2097152
```

#### Folder Management
```bash
# Create folder
uv run python main.py mkdir "My New Folder"

# Create folder in specific parent
uv run python main.py mkdir "Subfolder" --parent-id "1AbC2DeF3GhI4JkL5MnO6PqR7StU8VwX9Yz"
```

#### File Information
```bash
# Get detailed file info
uv run python main.py info "1AbC2DeF3GhI4JkL5MnO6PqR7StU8VwX9Yz"

# Check storage quota
uv run python main.py quota
```

#### Delete Files
```bash
# Delete file (with confirmation)
uv run python main.py delete "1AbC2DeF3GhI4JkL5MnO6PqR7StU8VwX9Yz"

# Delete file without confirmation
uv run python main.py delete "1AbC2DeF3GhI4JkL5MnO6PqR7StU8VwX9Yz" --confirm
```

### Sync Operations
```bash
# Sync single file
uv run python main.py sync "./document.pdf" "1AbC2DeF3GhI4JkL5MnO6PqR7StU8VwX9Yz"

# Sync entire directory (recursive)
uv run python main.py sync "./my_folder" "1AbC2DeF3GhI4JkL5MnO6PqR7StU8VwX9Yz" --recursive
```

## Configuration

Create a `.env` file to customize settings:

```env
# Google Drive API Configuration
GOOGLE_CREDENTIALS_FILE=credentials.json
GOOGLE_TOKEN_FILE=token.json

# Upload/Download Settings
DEFAULT_CHUNK_SIZE=1048576  # 1MB chunks
MAX_WORKERS=4              # Number of concurrent operations

# Progress Display Settings
PROGRESS_UPDATE_INTERVAL=0.1  # Seconds between progress updates
SHOW_TRANSFER_SPEED=true
SHOW_ETA=true

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=gdrive_operations.log
```

## File Structure

```
rclone_gdrive/
├── main.py              # CLI interface
├── gdrive_manager.py    # Core Google Drive operations
├── config.py           # Configuration settings
├── credentials.json    # Google API credentials (you provide)
├── token.json          # OAuth2 token (auto-generated)
├── downloads/          # Default download directory
├── uploads/            # Default upload directory
└── README.md           # This file
```

## Progress Tracking Features

The tool provides real-time progress tracking with:
- **Progress bars** with percentage completion
- **Transfer speed** (MB/s, KB/s)
- **ETA** (estimated time of arrival)
- **File size** information
- **Spinner animations** for operations in progress

## Error Handling

The tool handles common errors gracefully:
- **Authentication failures** with clear setup instructions
- **Network errors** with retry mechanisms
- **File not found** errors with helpful messages
- **Permission errors** with guidance

## Common Use Cases

### Backup Important Files
```bash
# Backup documents folder
uv run python main.py sync "./Documents" "backup_folder_id" --recursive
```

### Download All Photos
```bash
# List photos first
uv run python main.py list --query "mimeType contains 'image'"

# Download specific photos by ID
uv run python main.py download "photo_id" "./downloads/photo.jpg"
```

### Organize Files by Type
```bash
# Create organized folders
uv run python main.py mkdir "Images"
uv run python main.py mkdir "Documents"
uv run python main.py mkdir "Videos"

# Upload files to appropriate folders
uv run python main.py upload "./photo.jpg" --folder-id "images_folder_id"
```

## Troubleshooting

### Authentication Issues
- Ensure `credentials.json` is in the correct location
- Check that Google Drive API is enabled in your project
- Verify OAuth2 consent screen is configured

### Upload/Download Failures
- Check internet connection
- Verify file permissions
- Try reducing chunk size for large files
- Ensure sufficient Google Drive storage space

### Performance Optimization
- Increase chunk size for large files
- Use multiple workers for batch operations
- Monitor network bandwidth usage

## Security Notes

- Never commit `credentials.json` or `token.json` to version control
- Keep your Google Cloud project credentials secure
- Regularly review OAuth2 app permissions
- Use application-specific passwords when possible

## Contributing

Feel free to extend this boilerplate with additional features:
- Batch operations
- Resume interrupted transfers
- File versioning
- Encryption for sensitive files
- Integration with other cloud services

## License

This is boilerplate code for educational and development purposes.
