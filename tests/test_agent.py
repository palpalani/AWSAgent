"""Tests for AWS Agentic Agent."""

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from agentic_aws.agent import AWSAgenticAgent


class TestAWSAgenticAgent:
    """Tests for AWSAgenticAgent class."""

    @pytest.fixture
    def agent(
        self,
        mock_environment: None,  # noqa: ARG002
        mock_aws_session: MagicMock,
        mock_anthropic_client: MagicMock,
    ) -> AWSAgenticAgent:
        """Create an agent with mocked dependencies."""
        with (
            patch("boto3.Session", return_value=mock_aws_session),
            patch("anthropic.Anthropic", return_value=mock_anthropic_client),
        ):
            return AWSAgenticAgent()

    def test_agent_initialization(
        self,
        mock_environment: None,  # noqa: ARG002
        mock_aws_session: MagicMock,
        mock_anthropic_client: MagicMock,
    ) -> None:
        """Test that agent initializes successfully with valid credentials."""
        with (
            patch("boto3.Session", return_value=mock_aws_session),
            patch("anthropic.Anthropic", return_value=mock_anthropic_client),
        ):
            agent = AWSAgenticAgent()

        assert agent.client is not None
        assert agent.aws_config is not None

    def test_format_tools_returns_list(self, agent: AWSAgenticAgent) -> None:
        """Test that _format_tools returns a list of tool definitions."""
        tools = agent._format_tools()

        assert isinstance(tools, list)
        assert len(tools) > 0
        assert all("name" in tool for tool in tools)

    def test_format_tools_caches_result(self, agent: AWSAgenticAgent) -> None:
        """Test that _format_tools caches the result."""
        AWSAgenticAgent._tools = None

        tools1 = agent._format_tools()
        tools2 = agent._format_tools()

        assert tools1 is tools2

    def test_build_system_prompt_returns_string(self, agent: AWSAgenticAgent) -> None:
        """Test that _build_system_prompt returns a non-empty string."""
        prompt = agent._build_system_prompt()

        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "AWS" in prompt

    def test_execute_aws_operation_list_success(
        self,
        agent: AWSAgenticAgent,
        mock_aws_session: MagicMock,  # noqa: ARG002
    ) -> None:
        """Test successful list operation."""
        mock_cloudcontrol = MagicMock()
        mock_cloudcontrol.list_resources.return_value = {
            "ResourceDescriptions": [
                {"Properties": json.dumps({"BucketName": "test-bucket-1"})},
                {"Properties": json.dumps({"BucketName": "test-bucket-2"})},
            ]
        }

        with patch.object(agent.aws_config, "get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_session.client.return_value = mock_cloudcontrol
            mock_get_session.return_value = mock_session

            result = agent._execute_aws_operation(
                operation="list",
                resource_type="AWS::S3::Bucket",
            )

        assert result["status"] == "success"
        assert result["operation"] == "list"
        assert result["count"] == 2

    def test_execute_aws_operation_create_success(
        self,
        agent: AWSAgenticAgent,
    ) -> None:
        """Test successful create operation."""
        mock_cloudcontrol = MagicMock()
        mock_cloudcontrol.create_resource.return_value = {
            "ProgressEvent": {
                "RequestToken": "test-token-123",
                "OperationStatus": "IN_PROGRESS",
            }
        }

        with patch.object(agent.aws_config, "get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_session.client.return_value = mock_cloudcontrol
            mock_get_session.return_value = mock_session

            result = agent._execute_aws_operation(
                operation="create",
                resource_type="AWS::S3::Bucket",
                properties={"BucketName": "test-bucket"},
            )

        assert result["status"] == "success"
        assert result["operation"] == "create"
        assert result["request_token"] == "test-token-123"

    def test_execute_aws_operation_read_success(
        self,
        agent: AWSAgenticAgent,
    ) -> None:
        """Test successful read operation."""
        mock_cloudcontrol = MagicMock()
        mock_cloudcontrol.get_resource.return_value = {
            "ResourceDescription": {
                "Properties": json.dumps({"BucketName": "test-bucket"}),
            }
        }

        with patch.object(agent.aws_config, "get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_session.client.return_value = mock_cloudcontrol
            mock_get_session.return_value = mock_session

            result = agent._execute_aws_operation(
                operation="read",
                resource_type="AWS::S3::Bucket",
                identifier="test-bucket",
            )

        assert result["status"] == "success"
        assert result["operation"] == "read"
        assert result["properties"]["BucketName"] == "test-bucket"

    def test_process_request_text_response(
        self,
        agent: AWSAgenticAgent,
        mock_anthropic_client: MagicMock,
    ) -> None:
        """Test processing a request that returns a text response."""
        history: list[dict[str, Any]] = []

        with patch.object(agent, "client", mock_anthropic_client):
            result = agent.process_request("Hello", history)

        assert "test response" in result
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"

    def test_query_cloudwatch_logs_success(
        self,
        agent: AWSAgenticAgent,
    ) -> None:
        """Test successful CloudWatch logs query."""
        mock_logs = MagicMock()
        mock_logs.filter_log_events.return_value = {
            "events": [
                {
                    "timestamp": 1704067200000,
                    "message": "ERROR: Something went wrong",
                    "logStreamName": "test-stream",
                }
            ]
        }

        with patch.object(agent.aws_config, "get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_session.client.return_value = mock_logs
            mock_get_session.return_value = mock_session

            result = agent._query_cloudwatch_logs("test-function", hours_back=1)

        assert result["status"] == "success"
        assert result["function_name"] == "test-function"
        assert result["error_count"] == 1
