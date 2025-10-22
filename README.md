# ANA - Advanced Neural Assistant

> A personal AI assistant inspired by JARVIS from Iron Man, built with LiveKit and Google's Gemini model.

## Features

- 🎙️ **Voice**: Real-time voice interaction
- 🔌 **Extensible**: Easy-to-extend modular architecture
- 🌤️ **Weather**: Get current weather for any city
- 🔍 **Web Search**: Search the web using DuckDuckGo
- 📧 **Email**: Send emails through Gmail
- 💡 **LED Control**: Control Arduino-connected LEDs

## Quick Start

### Prerequisites

- Python 3.14+
- uv + ruff (not required, but recommended)
- Gmail account with App Password (for email features)
- Gemini free API key
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
GMAIL_USER=your-email@gmail.com
GMAIL_APP_PASSWORD=your-app-password
```

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
  }
}
```

Edit `config.json` to customize settings like Arduino port, model parameters, etc.

### Running ANA

```bash
# Run the agent
uv run main.py console
```

## Project Structure

```
ANA/
├── src/ana/              # Main package
│   ├── agent.py          # Agent implementation
│   ├── config.py         # Configuration loader
│   ├── prompts.py        # Prompt templates
│   └── tools/            # Modular tool system
│       ├── weather.py    # Weather tools
│       ├── search.py     # Search tools
│       ├── email.py      # Email tools
│       ├── hardware.py   # Arduino/LED control
│       └── system.py     # System control
├── config.json           # Application settings
├── .env                  # Credentials (not in git)
├── main.py               # Entry point
├── LICENSE               # MIT License
└── README.md             # This file
```

## Usage Examples

### Voice Commands

- "What's the weather in London?"
- "Search the web for Python tutorials"
- "Send an email to john@example.com"
- "Turn off the LED"
- "Turn on the LED for 10 seconds"
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
