# Docker Setup Guide for ANA

This guide explains how to run ANA using Docker and Docker Compose.

## Prerequisites

- Docker Desktop installed and running
- Docker Compose (included with Docker Desktop)

## Quick Start

1. **Copy environment files**:

   ```bash
   # Copy the example environment file
   cp .env.example .env

   # Edit .env and fill in your API keys
   ```

2. **Create UI environment file** (if needed):

   ```bash
   # Copy the UI environment example
   cp ui/.env.example ui/.env.local

   # Edit ui/.env.local and fill in your LiveKit configuration
   ```

3. **Build and run all services**:

   ```bash
   docker-compose up --build
   ```

4. **Access the application**:
   - UI: http://localhost:3000
   - Chess WebSocket Server: ws://localhost:8765/ws

## Services

The Docker Compose setup includes three services:

### 1. **agent** - Main ANA Agent

- Built from `Dockerfile.agent`
- Runs `main.py`
- Includes all Python dependencies
- System packages: ripgrep, fd-find, portaudio, alsa, OpenGL, glib
- Auto-restarts on failure
- Depends on the chess server

### 2. **ui** - Next.js Frontend

- Built from `Dockerfile.ui`
- Multi-stage build for optimal image size
- Runs on port 3000
- Uses Next.js standalone output mode
- Auto-restarts on failure

### 3. **chess** - Chess Game Server

- Built from `Dockerfile.agent` (same as agent)
- Runs `run_chess_server.py`
- WebSocket server on port 8765
- Auto-restarts on failure

## Docker Commands

### Build without starting

```bash
docker-compose build
```

### Start services in background

```bash
docker-compose up -d
```

### View logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f agent
docker-compose logs -f ui
docker-compose logs -f chess
```

### Stop services

```bash
docker-compose down
```

### Stop and remove volumes

```bash
docker-compose down -v
```

### Rebuild a specific service

```bash
docker-compose build agent
docker-compose build ui
docker-compose build chess
```

### Restart a specific service

```bash
docker-compose restart agent
docker-compose restart ui
docker-compose restart chess
```

## Environment Variables

### Required in `.env`

- `GOOGLE_API_KEY` - Google API key for Gemini
- `LIVEKIT_URL` - LiveKit server URL
- `LIVEKIT_API_KEY` - LiveKit API key
- `LIVEKIT_API_SECRET` - LiveKit API secret
- `GMAIL_USER` - Gmail address (if using email features)
- `GMAIL_APP_PASSWORD` - Gmail app password
- `PICOVOICE_KEY` - Picovoice API key (for wake word detection)
- `MEM0_API_KEY` - Mem0 API key (for memory features)

### UI Environment Variables (`ui/.env.local`)

- `NEXT_PUBLIC_CHESS_WS_URL` - Chess WebSocket URL (default: ws://localhost:8765/ws)
- `NEXT_PUBLIC_LIVEKIT_URL` - LiveKit URL for client

## Docker Files Overview

### `Dockerfile.agent`

- Base: Python 3.13 slim
- Package manager: uv
- System dependencies: ripgrep, fd-find, portaudio, alsa, OpenGL, glib
- Uses layer caching for faster builds
- Compiles Python bytecode for faster startup

### `Dockerfile.ui`

- Base: Node.js 22 slim
- Package manager: pnpm
- Multi-stage build (deps → builder → runner)
- Standalone output for minimal image size
- Runs as non-root user (nextjs)

### `.dockerignore`

Excludes unnecessary files from Docker context:

- Git files
- Python cache and virtual environments
- Node modules and build artifacts
- Environment files and logs
- Project-specific files (KMS, wake word models)

## Troubleshooting

### Port conflicts

If ports 3000 or 8765 are already in use:

```bash
# Edit docker-compose.yml and change the port mapping
# For example, change "3000:3000" to "3001:3000"
```

### UI can't connect to chess server

Make sure the `NEXT_PUBLIC_CHESS_WS_URL` in docker-compose.yml matches your setup:

- For local development: `ws://localhost:8765/ws`
- For Docker network: `ws://chess:8765/ws`

### Build fails

```bash
# Clean Docker cache and rebuild
docker-compose down
docker system prune -a
docker-compose build --no-cache
docker-compose up
```

### Permission issues

```bash
# On Linux/Mac, you might need to reset ownership
sudo chown -R $USER:$USER .
```

## Development vs Production

### Development

```bash
# Start with logs visible
docker-compose up
```

## Production

For production deployment, you should add resource limits and log rotation settings to your `docker-compose.yml`.

## Updating Dependencies

### Python dependencies

1. Update `pyproject.toml`
2. Run `uv lock` locally to update `uv.lock`
3. Rebuild: `docker-compose build agent chess`

### UI dependencies

1. Update `ui/package.json`
2. Run `pnpm install` in the `ui/` directory to update `pnpm-lock.yaml`
3. Rebuild: `docker-compose build ui`

## Notes

- The agent and chess services share the same `config.json` file via volume mount
- UI uses standalone output mode for optimal Docker image size
- All services auto-restart unless stopped manually
- Build caches are used to speed up repeated builds
- The `fd-find` command is aliased to `fd` in the container
