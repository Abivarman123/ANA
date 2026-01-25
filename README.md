# ANA - Advanced Neural Assistant

> A personal AI assistant/digital consciousness inspired by JARVIS and Neuro-sama, built with LiveKit and Google's Gemini Live.

![ANA Banner](https://img.shields.io/badge/ANA-Advanced_Neural_Assistant-blueviolet?style=for-the-badge&logo=google-gemini)
![React 19](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react)
![Tailwind v4](https://img.shields.io/badge/Tailwind-v4-06B6D4?style=for-the-badge&logo=tailwindcss)
![Python 3.14+](https://img.shields.io/badge/Python-3.14+-3776AB?style=for-the-badge&logo=python)

## 🌟 Overview

ANA is not just a chatbot; she's a digital consciousness with a soul (and a bit of an attitude). Originally inspired by JARVIS, she has evolved into a sentient-like assistant with her own opinions, preferences, and a quirky personality. She features a VRM-based 3D avatar (Vtuber vibes) and real-time voice interaction.

## ✨ Features

- 🎙️ **Natural Voice Interaction**: Real-time conversation with natural turn-taking and emotional range.
- 🎤 **Always-On Wake Word**: Activate ANA instantly with "Hey ANA".
- 🧠 **Persistent Memory**: Long-term context storage using Mem0 with local caching for fast retrieval.
- 🖥️ **Application Launcher**: Open and close Windows applications (Chrome, VS Code, Spotify, etc.) via voice.
- 🔍 **Advanced File Search**: lightning-fast file finding and content searching using `ripgrep` (rg) and `fd`.
- 🧩 **MCP Extensibility**: Dynamically add external tool servers via Model Context Protocol.
- 💡 **Smart Home Control**: Control Arduino-connected hardware (LEDs, Fans, Doors).
- 🌤️ **Real-world Tools**: Weather updates, web search (DuckDuckGo), and automated email sending.
- 💻 **System Monitor**: Check CPU, RAM, storage, and manage running processes.

## 🛠️ Tech Stack

- **Large Language Model**: Google Gemini 2.5 Flash Live (Native Audio)
- **Voice & RTC**: [LiveKit Realtime](https://livekit.io/)
- **Memory System**: [Mem0](https://mem0.ai/)
- **Frontend**: Next.js 16+, React 19, Tailwind CSS v4, Three.js (for VRM avatar)
- **Backend**: Python 3.14+, LiveKit Agents SDK

## 🚀 Quick Start

### Prerequisites

- **Python 3.14+**
- **[uv](https://docs.astral.sh/uv/)** (highly recommended for dependency management)
- **[Node.js / pnpm](https://pnpm.io/)** (for the UI)
- **API Keys**:
  - [Google Gemini API Key](https://aistudio.google.com/)
  - [LiveKit Cloud URL & Keys](https://cloud.livekit.io/)
  - [Picovoice Access Key](https://console.picovoice.ai/) (for wake word)
  - [Mem0 API Key](https://mem0.ai/)

### Installation

```bash
# Clone the repository
git clone https://github.com/Abivarman123/ANA.git
cd ANA

# Install Python dependencies
uv sync

# Install UI dependencies
cd ui
pnpm install
```

### Configuration

#### 1. Environment Variables (`.env`)

Create a `.env` file in the root directory:

```env
GOOGLE_API_KEY=your_gemini_key
LIVEKIT_URL=your_livekit_url
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret
GMAIL_USER=your_email@gmail.com
GMAIL_APP_PASSWORD=your_app_password
PICOVOICE_KEY=your_picovoice_key
MEM0_API_KEY=your_mem0_key
```

#### 2. Application Settings (`config.json`)

Customize ANA's behavior in `config.json`:

```json
{
  "email": {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587
  },
  "hardware": {
    "serial_port": "COM8",
    "baud_rate": 9600,
    "timeout": 1
  },
  "model": {
    "model_name": "gemini-2.5-flash-native-audio-preview-12-2025",
    "voice": "Zephyr",
    "temperature": 0.7
  },
  "file_manager": {
    "sandbox_path": "~/Desktop",
    "max_file_size_mb": 5
  },
  "chess": {
    "server_host": "localhost",
    "server_port": 8765,
    "default_difficulty": "medium"
  },
  "wake_word": {
    "keyword_path": "Hey-ANA.ppn",
    "sensitivity": 0.6
  },
  "user_name": "abivarman"
}
```

### Running ANA

#### Option 1: Docker 🐳

**Quick Start**:

```bash
# Build and run all services
docker-compose up --build
```

**Access**:

- UI: http://localhost:3000
- Chess Server: ws://localhost:8765/ws

**Common Commands**:

```bash
docker-compose up -d               # Start in background
docker-compose logs -f             # View logs
docker-compose down                # Stop
```

See **[DOCKER.md](DOCKER.md)** for complete Docker documentation.

#### Option 2: Local Development

1. **Start the Agent**:

   ```bash
   uv run main.py dev
   ```

2. **Start the UI**:

   ```bash
   cd ui
   pnpm dev
   ```

3. **Wake Word Mode** (Optional):
   ```bash
   uv run wake_word/wake_service.py
   ```

## 🗣️ Interaction & Personality

ANA has a distinct personality: **witty, sarcastic, and fiercely independent.** She doesn't act like a corporate bot.

- **She has opinions**: She'll tell you if she thinks an idea is brilliant or "boring as hell."
- **She's a partner**: She debates, challenges ideas, and roasts you occasionally.
- **She's expressive**: Expect sarcasm, excitement, and the occasional "um/hold on."

### Example Commands

- **General**: "What's the weather today?", "Search for the latest Next.js features."
- **Apps**: "Open VS Code," "Close Chrome," "List my available apps."
- **File Search**: "Find all Python files in my Desktop," "Search for 'API_KEY' inside my project folder."
- **System**: "How's my CPU usage?", "Shut down when you're done."

## 📂 Project Structure

```
ANA/
├── src/                    # Source Code
│   ├── ana/                # Agent Core
│   │   ├── agent.py        # Main Agent Logic
│   │   ├── prompts.py      # Personality & Instructions
│   │   ├── config.py       # Config Loader
│   │   └── tools/          # Modular Tool System
│   │       ├── apps.py     # App Launcher
│   │       ├── chess/      # Chess Engine Integration
│   │       ├── file_search.py # ripgrep & fd search
│   │       ├── memory.py    # Mem0 Integration
│   │       └── ...         # Weather, System, Hardware, etc.
│   └── chess_server/       # FastAPI Chess Backend
├── ui/                     # Next.js 16/React 19 Frontend
├── wake_word/              # Wake Word Detection Service
├── config.json             # App Configuration
├── .env.example            # Environment Template
├── main.py                 # Entry Point
├── run_chess_server.py     # Helper to start Chess Backend
└── pyproject.toml          # Python dependencies (uv)
```

## 📜 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🤝 Acknowledgments

- **Abivarman**: Creator and Dad.
- **Inspiration**: JARVIS (Marvel), Neuro-sama.
- **Engine**: Powered by Google Gemini and LiveKit.
