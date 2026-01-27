"""Tests for AWS configuration module."""

from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError, NoCredentialsError

from agentic_aws.config import AWSConfig
from agentic_aws.exceptions import AWSConnectionError


class TestAWSConfig:
    """Tests for AWSConfig class."""

    def test_init_loads_environment_variables(self, mock_environment: None) -> None:  # noqa: ARG002
        """Test that AWSConfig loads credentials from environment."""
        config = AWSConfig()

        assert config.access_key == "test-access-key"
        assert config.secret_key == "test-secret-key"
        assert config.region == "us-east-1"

    def test_init_uses_default_region(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that AWSConfig uses default region when not set."""
        monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")

        config = AWSConfig()

        assert config.region == "us-east-1"

    def test_get_session_returns_boto3_session(
        self,
        mock_environment: None,  # noqa: ARG002
        patched_boto3_session: MagicMock,
    ) -> None:
        """Test that get_session returns a boto3 Session."""
        config = AWSConfig()
        session = config.get_session()

        patched_boto3_session.assert_called_once_with(
            aws_access_key_id="test-access-key",
            aws_secret_access_key="test-secret-key",
            region_name="us-east-1",
        )
        assert session is not None

    def test_validate_connection_success(
        self,
        mock_environment: None,  # noqa: ARG002
        mock_aws_session: MagicMock,
    ) -> None:
        """Test successful connection validation."""
        with patch("boto3.Session", return_value=mock_aws_session):
            config = AWSConfig()
            result = config.validate_connection()

        assert result is True

    def test_validate_connection_raises_on_no_credentials(
        self,
        mock_environment: None,  # noqa: ARG002
    ) -> None:
        """Test that validate_connection raises AWSConnectionError on missing credentials."""
        mock_session = MagicMock()
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.side_effect = NoCredentialsError()
        mock_session.client.return_value = mock_sts

        with patch("agentic_aws.config.boto3.Session", return_value=mock_session):
            config = AWSConfig()
            with pytest.raises(AWSConnectionError, match="credentials not configured"):
                config.validate_connection()

    def test_validate_connection_raises_on_client_error(
        self,
        mock_environment: None,  # noqa: ARG002
    ) -> None:
        """Test that validate_connection raises AWSConnectionError on AWS API error."""
        mock_session = MagicMock()
        mock_sts = MagicMock()
        error_response = {"Error": {"Message": "Access Denied"}}
        mock_sts.get_caller_identity.side_effect = ClientError(error_response, "GetCallerIdentity")
        mock_session.client.return_value = mock_sts

        with patch("agentic_aws.config.boto3.Session", return_value=mock_session):
            config = AWSConfig()
            with pytest.raises(AWSConnectionError, match="AWS API error"):
                config.validate_connection()
