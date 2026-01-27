"""Shared test fixtures."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_aws_session() -> MagicMock:
    """Create a mock boto3 session."""
    session = MagicMock()

    sts_client = MagicMock()
    sts_client.get_caller_identity.return_value = {
        "Account": "123456789012",
        "Arn": "arn:aws:iam::123456789012:user/test-user",
        "UserId": "AIDAEXAMPLE",
    }

    cloudcontrol_client = MagicMock()
    logs_client = MagicMock()

    def client_factory(service_name: str, **_kwargs: Any) -> MagicMock:
        if service_name == "sts":
            return sts_client
        if service_name == "cloudcontrol":
            return cloudcontrol_client
        if service_name == "logs":
            return logs_client
        return MagicMock()

    session.client = client_factory
    return session


@pytest.fixture
def mock_anthropic_client() -> MagicMock:
    """Create a mock Anthropic client."""
    client = MagicMock()

    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = "This is a test response from the AI."

    response = MagicMock()
    response.content = [text_block]

    client.messages.create.return_value = response
    return client


@pytest.fixture
def sample_chat_history() -> list[dict[str, str]]:
    """Create sample conversation history."""
    return [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi! How can I help you manage your AWS infrastructure today?"},
    ]


@pytest.fixture
def mock_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set up mock environment variables."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test-access-key")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret-key")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")


@pytest.fixture
def patched_boto3_session(mock_aws_session: MagicMock) -> Any:
    """Patch boto3.Session to return mock session."""
    with patch("boto3.Session", return_value=mock_aws_session) as patched:
        yield patched
