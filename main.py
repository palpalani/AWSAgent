"""FastAPI application for the AWS Agentic Agent."""

import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from agentic_aws.exceptions import AWSAgentError
from agentic_aws.logging import get_logger, setup_logging
from agentic_aws.models import ChatRequest, ChatResponse
from agentic_aws.processor import process_request

load_dotenv()

setup_logging(level=os.getenv("LOG_LEVEL", "INFO"))
logger = get_logger(__name__)

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:8501,http://127.0.0.1:8501").split(",")

RATE_LIMIT = os.getenv("RATE_LIMIT", "10/minute")

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Agentic AWS API",
    description="AI-powered AWS infrastructure management through natural language",
    version="0.1.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.get("/")
def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "Agentic AWS API is running"}


@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint for liveness probes."""
    return {"status": "healthy"}


@app.get("/ready")
def ready() -> dict[str, str | bool]:
    """Readiness check endpoint that verifies AWS connectivity."""
    from agentic_aws.config import AWSConfig

    try:
        config = AWSConfig()
        config.validate_connection()
        return {"status": "ready", "aws_connected": True}
    except Exception as e:
        logger.warning(f"Readiness check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail={"status": "not_ready", "aws_connected": False, "error": str(e)},
        ) from e


@app.post("/chat", response_model=ChatResponse)
@limiter.limit(RATE_LIMIT)
def chat(request: ChatRequest, http_request: Request) -> ChatResponse:
    """Process a chat message and return the agent's response."""
    logger.info(
        "Processing chat request",
        extra={"extra_data": {"client_ip": get_remote_address(http_request)}},
    )

    try:
        history = [msg.model_dump() for msg in request.history]
        response = process_request(request.message, history)

        updated_history = [{"role": msg["role"], "content": msg["content"]} for msg in history]

        return ChatResponse(
            response=response,
            updated_history=updated_history,
        )

    except AWSAgentError as e:
        logger.error(f"AWS Agent error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
