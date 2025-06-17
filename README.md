# 🧠 TaskMind - Multi-Agent AI Network


https://github.com/user-attachments/assets/c9d39b8d-2026-4ded-9688-36a95e790998


| [![Demo 1](https://img.youtube.com/vi/T4W0Y_quT7A/0.jpg)](https://www.youtube.com/watch?v=T4W0Y_quT7A) | [![Demo 2](https://img.youtube.com/vi/1kjYtHB1N2k/0.jpg)](https://www.youtube.com/watch?v=1kjYtHB1N2k) |
|:--:|:--:|
| [Watch Agent Demo](https://www.youtube.com/watch?v=T4W0Y_quT7A) | [Watch Transcription Demo](https://www.youtube.com/watch?v=1kjYtHB1N2k) |
> **Intelligent Problem-Solving Through Specialized AI Agents**

TaskMind is a sophisticated multi-agent AI system that intelligently routes user problems to specialized agents, each equipped with powerful boilerplate code for rapid solution deployment. Built with intelligence and Telegram integration, it creates a seamless experience for complex technical tasks.

## 🌟 Key Features

### 🤖 Multi-Agent Architecture
- **Main Agent/Telegram Bot** - Conversational problem understanding and intelligent routing
- **Specialized Meta Agents** - Domain-specific problem solvers with dedicated boilerplates
- **Cross-Agent Collaboration** - Agents can combine boilerplates for complex multi-step solutions

### ⚡ Intelligent Boilerplate System
- **Rapid Deployment** - Pre-built, production-ready code templates
- **Modular Design** - Mix and match boilerplates for complex workflows
- **Cloud-Optimized** - Resource-efficient processing on cloud infrastructure

### 🚀 Cloud Integration
- **Novita AI GPU Cloud** - Automated FFmpeg with CUDA acceleration
- **Resource Optimization** - Offload heavy processing to save local resources
- **Scalable Infrastructure** - Handle demanding tasks efficiently

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   User Input    │───▶│   Main Agent     │───▶│ Specialized     │
│  (Telegram)     │    │  (GPT-4o Router) │    │ Meta Agents     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │ Problem Analysis │    │   Boilerplate   │
                       │ & Agent Selection│    │   Execution     │
                       └──────────────────┘    └─────────────────┘
```

## 🤖 Specialized Agents

| Agent | Purpose | Boilerplate | Cloud Features |
|-------|---------|-------------|----------------|
| 🕷️ **Web Scraper** | Data extraction & crawling | `firecrawl_boilerplate` | Distributed scraping |
| 📁 **File Manager** | Cloud storage & sync | `rclone_gdrive` | Google Drive integration |
| 🎵 **Audio Agent** | Speech processing | `whisper` | Cloud transcription |
| 🎬 **Video Agent** | Media processing | `yt-dlp` + `ffmpeg` | GPU-accelerated encoding |
| 📄 **PDF Processor** | Document analysis | `pdf_utils` | Batch processing |

## 🛠️ Boilerplate Components

### 🕷️ Web Scraping (`firecrawl_boilerplate`)
- **Firecrawl API Integration** - Professional web scraping
- **Schema Generation** - Automatic data structure creation
- **Rate Limiting** - Respectful crawling practices
- **Error Handling** - Robust failure recovery

### 📁 Cloud Storage (`rclone_gdrive`)
- **OAuth2 Authentication** - Secure Google Drive access
- **Live Progress Tracking** - Real-time upload/download status
- **Sync Operations** - Bidirectional folder synchronization
- **Storage Management** - Quota monitoring and optimization

### 🎵 Audio Processing (`whisper`)
- **Speech-to-Text** - High-accuracy transcription
- **Multi-language Support** - Global language processing
- **Batch Processing** - Efficient bulk operations
- **Cloud Optimization** - Resource-efficient processing

### 🎬 Video Processing (`yt-dlp` + `ffmpeg`)
- **YouTube Download** - High-quality video extraction
- **GPU Acceleration** - NVIDIA NVENC/NVDEC support
- **Format Conversion** - Comprehensive codec support
- **Streaming Optimization** - Web-ready output formats

## ⚡ Cloud Automation

### 🎯 Novita AI Integration
TaskMind leverages [Novita AI](https://novita.ai/) for GPU-accelerated processing:

- **50% Cost Reduction** - Efficient cloud GPU utilization
- **High Performance** - Up to 300 tokens/second processing
- **Global Distribution** - Optimized worldwide access
- **Automated Setup** - One-click FFmpeg + CUDA installation

### 🔧 Automated Installation Scripts
```bash
# FFmpeg with CUDA support
./ffmpeg.sh

# YouTube downloader setup
./yt-dlp.sh
```

## 🚀 Quick Start

### 1. Environment Setup
```bash
# Clone the repository
git clone <repository-url>
cd TaskLm

# Install dependencies
uv sync

# Setup environment variables
cp config/tokens.env.example .env
# Edit .env with your API keys
```

### 2. Configure API Keys
```bash
# Required tokens in .env
OPENAI_API_KEY=your_openai_key
MAIN_AGENT_TOKEN=your_telegram_bot_token
FIRECRAWL_API_KEY=your_firecrawl_key
```

### 3. Test the System
```bash
# Test main agent (no token required)
uv run test_main_agent.py

# Setup with real tokens
uv run setup_main_agent.py
```

### 4. Launch Main Agent
```bash
# Start the main Telegram bot
uv run src/main_agent.py
```

## 💡 Usage Examples

### 🎬 Complex Workflow: YouTube → Transcription → Cloud Storage
```
User: "Download this YouTube video, transcribe it, and save to Google Drive"

1. Main Agent analyzes request
2. Routes to Video Agent (yt-dlp download)
3. Chains to Audio Agent (Whisper transcription)
4. Chains to File Manager (Google Drive upload)
5. Returns organized results to user
```

### 🕷️ Web Scraping with Analysis
```
User: "Scrape product data from this e-commerce site and analyze trends"

1. Web Scraper Agent extracts data
2. Generates structured schema
3. Processes with cloud resources
4. Returns analysis and insights
```

## 🔧 Development with Trae IDE

TaskMind is optimized for development in [Trae IDE](https://s.trae.ai/a/63be3b) with three integrated MCP (Model Context Protocol) servers:

- **Enhanced Code Intelligence** - AI-powered development assistance
- **Integrated Debugging** - Seamless error detection and resolution
- **Collaborative Development** - Multi-agent code generation and review

## 📁 Project Structure

```
TaskLm/
├── src/                          # Core agent implementations
│   ├── main_agent.py            # Main routing agent
│   ├── web_scraper_meta_agent.py # Web scraping specialist
│   └── web_page_analyzer.py     # Page analysis utilities
├── boiler_plate/                 # Reusable code templates
│   ├── firecrawl_boilerplate/   # Web scraping tools
│   ├── rclone_gdrive/           # Cloud storage integration
│   ├── whisper/                 # Audio processing
│   ├── yt-dlp/                  # Video downloading
│   └── telegram_bot.py          # Bot framework
├── config/                       # Configuration templates
├── ffmpeg.sh                    # GPU acceleration setup
└── pyproject.toml               # Project dependencies
```

## 🤝 Contributing

1. **Fork the Repository**
2. **Create Feature Branch** - `git checkout -b feature/amazing-feature`
3. **Add Boilerplate** - Create new specialized agents
4. **Test Integration** - Ensure cross-agent compatibility
5. **Submit Pull Request** - Share your improvements

## 📋 Requirements

- **Python 3.13+** with uv package manager
- **OpenAI API Key** for GPT-4o intelligence
- **Telegram Bot Token** for user interaction
- **Optional**: Firecrawl, Google Drive, Novita AI keys for full functionality

## 🔮 Future Roadmap

- [ ] **Voice Interface** - Audio input/output support
- [ ] **Visual Agents** - Image and video analysis
- [ ] **Database Integration** - Persistent data storage
- [ ] **API Gateway** - REST/GraphQL interfaces
- [ ] **Monitoring Dashboard** - Real-time agent performance
- [ ] **Custom Boilerplates** - User-defined agent templates

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

