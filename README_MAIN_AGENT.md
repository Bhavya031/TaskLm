# TaskMind Main Agent - Testing Guide

## 🎯 Main Agent Overview

The **Main Agent** is the entry point for the TaskMind Meta-Agent system. It:

- Routes users to appropriate specialized Meta Agents
- Analyzes user requests using keyword matching
- Provides interactive menu system with buttons
- Manages the overall user experience

## ✅ Test Results

The Main Agent has been tested and verified working:

```
✅ All Main Agent tests passed!
✅ Environment setup complete
✅ Request analysis working (routes to correct Meta Agent)
✅ Interactive keyboard buttons working
✅ All 5 Meta Agent configurations loaded
```

## 🚀 Quick Start

### 1. Run Tests (No Token Required)
```bash
uv run test_main_agent.py
```

### 2. Setup with Real Token
```bash
uv run setup_main_agent.py
```

### 3. Start Main Agent
```bash
uv run src/main_agent.py
```

## 🤖 Meta Agents Configured

The Main Agent is configured to route to these Meta Agents:

| Agent | Purpose | Boilerplate |
|-------|---------|-------------|
| 🕷️ Web Scraper | Data extraction & crawling | `firecrawl_boilerplate` |
| 📁 File Manager | File operations & cloud storage | `rclone_gdrive` |
| 🎵 Audio | Audio processing & transcription | `whisper` |
| 🎬 Video | Video processing & downloading | `ytdlp_downloader.py`, `ffmpeg_processor.py` |
| 🤖 Telegram | Advanced Telegram bot features | `telegram_bot.py` |

## 🧪 Testing Examples

The Main Agent correctly analyzes these requests:

- **"I want to scrape product prices"** → Routes to 🕷️ Web Scraper Meta Agent
- **"Create a bot to backup files"** → Routes to 📁 File Manager Meta Agent  
- **"I need audio transcription"** → Routes to 🎵 Audio Meta Agent
- **"Build a YouTube downloader"** → Routes to 🎬 Video Meta Agent
- **"Make an advanced bot"** → Routes to 🤖 Telegram Meta Agent

## 📁 Project Structure

```
TaskMind/
├── src/
│   └── main_agent.py          # Main Agent implementation
├── config/
│   └── tokens.env.example     # Token configuration template
├── boiler_plate/              # Available boilerplates
│   ├── telegram_bot.py
│   ├── ytdlp_downloader.py
│   ├── ffmpeg_processor.py
│   ├── firecrawl_boilerplate/
│   ├── rclone_gdrive/
│   └── whisper/
├── test_main_agent.py         # Test suite
└── setup_main_agent.py        # Setup script
```

## ⚡ Next Steps

1. **Test Main Agent** ✅ (Complete)
2. **Build Meta Agent System** (Next phase)
3. **Integrate Goose CLI** (For code generation)
4. **Add token management** (For generated agents)
5. **Create deployment scripts**

## 🔑 Token Requirements

- **Main Agent**: 1 token (`MAIN_AGENT_TOKEN`)
- **Meta Agents**: 5 tokens (one per specialist agent)
- **Generated Agents**: Pool of tokens for created bots

## 💡 Key Features Tested

- ✅ Natural language request analysis
- ✅ Interactive button navigation
- ✅ Command handling (`/start`, `/help`, `/agents`)
- ✅ Error handling and validation
- ✅ Meta Agent routing logic
- ✅ Boilerplate path resolution

## 🎮 Interactive Testing

Run the interactive test to try different scenarios:

```bash
uv run test_main_agent.py
# Choose "y" for interactive test
```

**The Main Agent is ready!** 🎉

Once you've tested it with a real Telegram token, we can proceed to build the Meta Agent system.