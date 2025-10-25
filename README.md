# ANA - Advanced Neural Assistant

> A personal AI assistant inspired by JARVIS from Iron Man, built with LiveKit and Google's Gemini model.

## Features

- 🎙️ **Voice**: Real-time voice interaction
- 🎤 **Wake Word**: Always-on "Hey ANA" voice activation
- 🧠 **Long‑term Memory**: Persist user context with Mem0 (project-level custom instructions)
- 🧩 **MCP Extensibility**: Add external tool servers dynamically
- 🔌 **Extensible**: Easy-to-extend modular architecture
- 🌤️ **Weather**: Get current weather for any city
- 🔍 **Web Search**: Search the web using DuckDuckGo
- 📧 **Email**: Send emails through Gmail
- 💡 **LED Control**: Control Arduino-connected LEDs
- 📁 **File Manager**: Safe file operations on Desktop (sandboxed)
- 💻 **System Monitor**: Check CPU, RAM, storage, and running processes

## Quick Start

### Prerequisites

- Python 3.14+
- uv + ruff (not required, but recommended)
- Gmail account with App Password (for email features)
- Gemini free API key
- Picovoice Access Key (free, for wake word detection)
- Arduino (optional, for LED control)

### Installation

```bash
# Clone the repository
git clone https://github.com/Abivarman123/ANA.git
cd ANA

# Install dependencies
uv sync
```

### Configuration

#### 1. Environment Variables (Credentials)

Create a `.env` file with your sensitive credentials:

```env
GOOGLE_API_KEY=gemini api key
LIVEKIT_URL=livekit url
LIVEKIT_API_KEY=livekit api key
LIVEKIT_API_SECRET=livekit api secret
GMAIL_USER=gmail account
GMAIL_APP_PASSWORD=gmail app password
PICOVOICE_KEY=pico voice key
MEM0_API_KEY=mem0 api key
```

Get your free Picovoice key from: https://console.picovoice.ai/

**Note:** Only credentials go in `.env`. All other settings (sensitivity, ports, etc.) are in `config.json`.

#### 2. Application Settings (config.json)

All non-sensitive settings are in `config.json`:

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
    "model_name": "gemini-2.5-flash-native-audio-preview-09-2025",
    "voice": "Aoede",
    "temperature": 0.8
  },
  "file_manager": {
    "sandbox_path": "~/Desktop",
    "max_file_size_mb": 5
  },
  "wake_word": {
    "keyword_path": "Hey-ANA.ppn",
    "sensitivity": 0.5,
    "max_retries": 5,
    "retry_delay_seconds": 5
  },
  "mcp_servers": [],
  "user_name": "abivarman"
}
```

Edit `config.json` to customize settings like Arduino port, model parameters, etc.

### Running ANA

#### Standard Mode
```bash
# Run the agent
uv run main.py console
```

#### Wake Word Mode (Always-On Voice Activation)

```bash
python wake_service.py
```

Say **"Hey ANA"** to activate!

## Memory (Mem0)

- ANA initializes a Mem0 client on startup and sets project-level custom instructions to store only meaningful, long-term info.
- Custom instructions apply only to new memories added after initialization. Existing memories are not retroactively filtered.
- Configure Mem0 via:
  - `.env`: set `MEM0_API_KEY`
  - `config.json`: set `user_name` for per-user memories

Tools related to memory live in `src/ana/tools/memory.py`:
- `search_memories(query, limit)` retrieves relevant past info
- `get_recent_memories(count)` fetches latest stored facts

## Project Structure

```
ANA/
├── src/ana/                      # Main package
│   ├── agent.py                  # Agent implementation
│   ├── config.py                 # Configuration loader
│   ├── prompts.py                # Prompt templates
│   ├── wake_word.py              # Wake word detection module
│   └── tools/                    # Modular tool system
│       ├── weather.py            # Weather tools
│       ├── search.py             # Search tools
│       ├── email.py              # Email tools
│       ├── hardware.py           # Arduino/LED control
│       ├── memory.py             # Long-term memory (Mem0) tools & helpers
│       └── system.py             # System control & monitoring (shutdown, system info)
│── wake_word/
│   ├── Hey-ANA.ppn               # Wake word model file
│   ├── start_wake_service.bat    # Start wake word service
│   ├── stop_wake_service.bat     # Stop wake word service
│   └── wake_service.py           # Wake word background service
├── config.json                   # Application settings
├── .env                          # Credentials (not in git)
├── main.py                       # Entry point
├── LICENSE                       # MIT License
└── README.md                     # This file
```

## Usage Examples

### Voice Commands

**Wake Word:**
- "Hey ANA" - Activates the assistant (when wake word service is running)

**General:**
- "What's the weather in London?"
- "Search the web for Python tutorials"
- "Send an email to john@example.com"

**LED Control:**
- "Turn on the LED"
- "Turn off the LED"
- "Turn on the LED for 10 seconds"

**File Management:**
- "Create a file called notes.txt with content 'Hello World'"
- "Read the file notes.txt"
- "Edit notes.txt and change the content to 'Updated content'"
- "List all files on my Desktop"
- "Delete the file notes.txt"

**System Monitoring:**
- "What's my system status?"
- "Check RAM usage"
- "Show me CPU usage"
- "How much storage do I have?"
- "Which processes are using the most memory?"

**System:**
- "Shut down ANA"

### Personality

ANA speaks like a classy butler with a touch of sarcasm, similar to JARVIS:

- "Will do, Sir"
- "Roger Boss"
- "Check!"

## Architecture

The project uses a modular architecture for easy extension and maintenance:

- **Configuration**: Centralized in `config.py`, only credentials from env
- **Tools**: Each category in its own file with a registry system
- **Agent**: Clean separation of concerns
- **Prompts**: Template-based prompt management
- **Memory**: Mem0 project-level custom instructions with verification and logging
- **Shutdown**: Graceful shutdown triggers memory save and closes terminal on Windows

## MCP (Model Context Protocol)

- Configure external tool servers via `mcp_servers` in `config.json` (array of URLs)
- Servers are auto-initialized and exposed as tools to the agent

## Development

### Adding Dependencies

```bash
# Add to pyproject.toml, then:
uv sync
```

### Code Style

- Use type hints
- Add docstrings to all tools
- Follow existing patterns
- Keep files under 400 LOC

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Author

**Abivarman**

## Acknowledgments

- Inspired by JARVIS from Iron Man
- Built with [LiveKit](https://livekit.io/)
- Powered by [Google Gemini](https://deepmind.google/technologies/gemini/)
