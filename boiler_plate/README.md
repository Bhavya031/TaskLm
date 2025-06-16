# 🚀 Boilerplate Collection

A comprehensive collection of Python boilerplates for rapid development. Each boilerplate is production-ready with proper error handling, progress tracking, and modern Python practices.

## 📁 Directory Structure

```
boiler_plate/
├── firecrawl_boilerplate/     # Web scraping with structured data extraction
├── whisper/                   # Audio transcription using OpenAI Whisper
├── rclone_gdrive/            # Google Drive operations with progress tracking
├── pdf-processor/            # PDF manipulation and conversion toolkit
├── telegram_bot.py           # Complete Telegram bot framework
├── ffmpeg_processor.py       # Video/audio processing with hardware acceleration
├── ytdlp_downloader.py       # YouTube video/audio downloader
└── yt_dlp_usage_example.py   # Simple YouTube download example
```

## 🔧 Available Boilerplates

### 1. 🌐 Firecrawl Web Scraping (`firecrawl_boilerplate/`)
**Purpose**: Intelligent web scraping with AI-powered data extraction

**Key Files**:
- `schema_generator.py` - Auto-generates Pydantic schemas from web pages using LLM
- `firecrawl_example.py` - Example of structured data extraction
- `pyproject.toml` - Project configuration with Firecrawl dependencies

**Use Cases**: E-commerce price monitoring, content extraction, data collection
**CLI Usage**: `uv run schema_generator.py https://example.com --output schema.txt`

### 2. 🎵 Whisper Audio Transcription (`whisper/`)
**Purpose**: Audio-to-text transcription with timestamp support

**Key Files**:
- `main.py` - Audio transcription with Whisper models
- `pyproject.toml` - Whisper and PyTorch dependencies

**Use Cases**: Meeting transcriptions, podcast subtitles, voice note processing
**CLI Usage**: `uv run main.py --audio file.mp3 --model turbo`

### 3. ☁️ Google Drive Manager (`rclone_gdrive/`)
**Purpose**: Complete Google Drive operations with beautiful CLI interface

**Key Files**:
- `main.py` - CLI interface for all Drive operations
- `gdrive_manager.py` - Core Google Drive API operations
- `config.py` - Configuration and settings management

**Use Cases**: File backup, cloud storage automation, Drive API integration
**CLI Usage**: `uv run main.py upload file.pdf --folder-id YOUR_FOLDER_ID`

### 4. 📄 PDF Processor (`pdf-processor/`)
**Purpose**: Comprehensive PDF manipulation toolkit

**Key Files**:
- `pdf_core.py` - Core PDF operations (merge, split, compress)
- `pdf_converter.py` - File format conversions to PDF
- `main.py` - Interactive PDF processing interface

**Use Cases**: Document processing, PDF automation, batch conversions
**CLI Usage**: `uv run main.py --interactive`

### 5. 🤖 Telegram Bot Framework (`telegram_bot.py`)
**Purpose**: Full-featured Telegram bot with progress bars and file handling

**Key Features**:
- Progress tracking with visual indicators
- File upload/download with progress bars
- Inline keyboards and styled text
- Error handling and logging
- Modular design for custom handlers

**Use Cases**: Automation bots, file processing bots, notification systems
**Usage**: Import and customize the `TelegramBot` class

### 6. 🎬 FFmpeg Media Processor (`ffmpeg_processor.py`)
**Purpose**: Advanced video/audio processing with hardware acceleration

**Key Features**:
- NVIDIA NVENC hardware acceleration support
- Video compression, conversion, and optimization
- Audio extraction and processing
- Streaming optimization
- Comprehensive media analysis

**Use Cases**: Video compression, format conversion, streaming preparation
**Usage**: Interactive CLI for media processing tasks

### 7. 📺 YouTube Downloader (`ytdlp_downloader.py`)
**Purpose**: YouTube video/audio downloader with quality selection

**Key Features**:
- Quality selection interface
- Progress bars with download speed
- Support for both `youtube.com` and `youtu.be` URLs
- Batch download capabilities
- Audio-only extraction

**Use Cases**: Content archiving, offline viewing, audio extraction
**Usage**: `YouTubeDownloader` class with interactive quality selection

### 8. 🔗 Simple YouTube Example (`yt_dlp_usage_example.py`)
**Purpose**: Basic YouTube download example for quick testing

**Use Cases**: Simple video downloads, learning yt-dlp basics

## 🚀 Quick Start Guide

### Setting Up a New Project

1. **Create project directory**:
   ```bash
   mkdir my_project && cd my_project
   uv init
   ```

2. **Copy boilerplate**:
   ```bash
   cp -r ../boiler_plate/telegram_bot.py .
   cp -r ../boiler_plate/firecrawl_boilerplate .
   ```

3. **Install dependencies**:
   ```bash
   uv add python-telegram-bot firecrawl-py python-dotenv
   ```

4. **Create your handler**:
   ```python
   from telegram_bot import TelegramBot
   
   def my_handler(message_text=None, callback_data=None, progress_callback=None):
       return {"type": "text", "content": f"You said: {message_text}"}
   
   bot = TelegramBot("YOUR_BOT_TOKEN", my_handler)
   bot.run()
   ```

### Environment Variables Required

Create `.env` file with necessary API keys:
```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

# Firecrawl
FIRECRAWL_API_KEY=your_firecrawl_api_key

# OpenAI (for schema generation)
OPENAI_API_KEY=your_openai_api_key

# Google Drive (if using)
GOOGLE_CREDENTIALS_FILE=credentials.json
```

## 🛠 Combining Boilerplates

### Example: Price Monitoring Bot
Combine Telegram Bot + Firecrawl for price tracking:

```python
from telegram_bot import TelegramBot, TelegramBotResponse
from firecrawl_boilerplate.price_extractor import extract_price

def price_handler(message_text=None, callback_data=None, progress_callback=None):
    if message_text and message_text.startswith('/price'):
        url = message_text.replace('/price ', '')
        price_data = extract_price(url)
        return TelegramBotResponse.text(f"Current price: ${price_data['price']}")
    
    return TelegramBotResponse.text("Send /price <url> to check prices")

bot = TelegramBot(os.getenv("TELEGRAM_BOT_TOKEN"), price_handler)
bot.run()
```

### Example: Media Processing Bot
Combine Telegram Bot + FFmpeg + YouTube Downloader:

```python
def media_handler(message_text=None, callback_data=None, progress_callback=None):
    if 'youtube.com' in message_text:
        # Download and process video
        downloader = YouTubeDownloader()
        processor = MediaProcessor()
        # ... processing logic
    
    return TelegramBotResponse.progress("Processing video...", "Done!", 100)
```

## 📖 Documentation

Each boilerplate includes:
- **README.md** - Detailed usage instructions
- **Example files** - Working examples and demos
- **CLI interfaces** - Command-line usage patterns
- **API documentation** - Class and method descriptions

## 🔗 Dependencies Management

All boilerplates use `uv` for dependency management:
- `pyproject.toml` - Project configuration
- `uv add package` - Add new dependencies
- `uv run script.py` - Run scripts in virtual environment
- `uv sync` - Install all dependencies

## 💡 Best Practices

1. **Environment Variables**: Use `.env` files for API keys
2. **Error Handling**: All boilerplates include comprehensive error handling
3. **Progress Tracking**: Long operations show progress to users
4. **Logging**: Structured logging for debugging and monitoring
5. **Testing**: Include test files and examples
6. **Documentation**: Clear usage examples and API documentation

## 🤝 Contributing

When adding new boilerplates:
1. Include comprehensive README
2. Add CLI interface if applicable
3. Include working examples
4. Use consistent error handling patterns
5. Add progress tracking for long operations
6. Include test files

## 📝 License

Each boilerplate is designed for reuse in your projects. Modify and adapt as needed for your specific requirements. 