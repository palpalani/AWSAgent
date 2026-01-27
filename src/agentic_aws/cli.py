"""CLI entry points for agentic-aws."""

import subprocess
import sys
from pathlib import Path


def run_api() -> None:
    """Run the FastAPI server."""
    subprocess.run(
        [sys.executable, "-m", "uvicorn", "main:app", "--reload", "--port", "8000"],
        cwd=Path(__file__).parent.parent.parent,
        check=False,
    )


def run_chat() -> None:
    """Run the Streamlit chat interface."""
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", "chat.py", "--server.port", "8501"],
        cwd=Path(__file__).parent.parent.parent,
        check=False,
    )


if __name__ == "__main__":
    run_api()
