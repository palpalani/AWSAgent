# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI-powered AWS infrastructure management system that allows managing cloud resources through natural language conversations. It uses Claude AI with function calling to interact with AWS Cloud Control API.

## Architecture

```
Streamlit (chat.py) → FastAPI (main.py) → processor.py → AWSAgenticAgent (agent.py) → AWS APIs
```

### Project Structure

```
agentic-aws-resource-management/
├── src/
│   └── agentic_aws/
│       ├── __init__.py          # Package init with exports
│       ├── agent.py             # Core agent logic
│       ├── cli.py               # CLI entry points
│       ├── config.py            # AWS session management
│       ├── exceptions.py        # Custom exceptions
│       ├── models.py            # Pydantic request/response models
│       ├── processor.py         # Request processor with singleton
│       ├── prompts.py           # System prompts
│       └── tools.json           # Tool definitions for Claude
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Shared fixtures
│   ├── test_config.py           # AWS config tests
│   └── test_agent.py            # Agent tests
├── main.py                      # FastAPI application
├── chat.py                      # Streamlit frontend
├── pyproject.toml               # Package configuration (uv/hatch)
├── uv.lock                      # Lock file for reproducible builds
├── .env.example                 # Environment template
└── CLAUDE.md
```

### Key Components

- **chat.py**: Streamlit frontend using httpx for API calls
- **main.py**: FastAPI server with `/chat` endpoint using Pydantic models for validation
- **src/agentic_aws/processor.py**: Singleton pattern wrapper for agent instance
- **src/agentic_aws/agent.py**: Core agent logic - handles Claude API calls with tools, executes AWS operations
- **src/agentic_aws/config.py**: AWS session management with proper exception handling
- **src/agentic_aws/prompts.py**: System prompts for the AI agent
- **src/agentic_aws/models.py**: Pydantic models with TypeAlias for typed literals
- **src/agentic_aws/exceptions.py**: Custom exceptions (AWSAgentError, AWSConnectionError, ToolExecutionError)
- **src/agentic_aws/cli.py**: CLI entry points for running the API and chat

## Common Commands

### Setup (using uv)

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install all dependencies (creates venv automatically)
uv sync --all-extras
```

### Running the Application

```bash
# Start FastAPI backend (port 8000)
uv run uvicorn main:app --reload --port 8000

# Start Streamlit frontend (port 8501)
uv run streamlit run chat.py --server.port 8501

# Or use CLI entry points
uv run agentic-aws-api
uv run agentic-aws-chat
```

### Development

```bash
# Run linting
uv run ruff check src tests main.py chat.py

# Run formatter
uv run ruff format src tests main.py chat.py

# Run type checking
uv run mypy src

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=src
```

### Environment Variables

Required in `.env` (see `.env.example`):
- `ANTHROPIC_API_KEY`: Claude API key
- `AWS_ACCESS_KEY_ID`: AWS access key
- `AWS_SECRET_ACCESS_KEY`: AWS secret key
- `AWS_DEFAULT_REGION`: AWS region (defaults to us-east-1)
- `API_URL`: Backend URL for frontend (defaults to http://localhost:8000)

## Key Implementation Details

- The agent uses Claude 3.5 Sonnet (`claude-3-5-sonnet-latest`) for both tool selection and summary generation
- AWS operations are executed via Cloud Control API (cloudcontrol client) which is async - resources may not be immediately available
- Conversation history is passed from Streamlit → FastAPI → agent and back to maintain context
- Tool results are processed through a summary generation step to provide natural language responses
- AWS connection is validated on agent initialization; Anthropic connection is tested on first use
- Singleton pattern used for agent to avoid repeated initialization
- Type hints throughout with TypeAlias for Literal types (Python 3.11+ compatible)
- Custom exceptions for specific error handling
- Pydantic v2 models for request/response validation with model_config
- Uses httpx instead of requests for modern async-capable HTTP client
