"""AWS session configuration and connection management."""

import os

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from dotenv import load_dotenv

from agentic_aws.exceptions import AWSConnectionError
from agentic_aws.logging import get_logger

load_dotenv()

logger = get_logger(__name__)


class AWSConfig:
    """Manages AWS session configuration and connection validation."""

    def __init__(self) -> None:
        self.access_key: str | None = os.getenv("AWS_ACCESS_KEY_ID")
        self.secret_key: str | None = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.region: str = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

    def get_session(self) -> boto3.Session:
        """Get AWS session with configured credentials."""
        return boto3.Session(
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
        )

    def validate_connection(self) -> bool:
        """Test AWS connection and return True if successful.

        Raises:
            AWSConnectionError: If connection fails.
        """
        try:
            session = self.get_session()
            sts = session.client("sts")
            identity = sts.get_caller_identity()
            logger.info(f"AWS Connection successful! Account: {identity['Account']}")
            return True

        except NoCredentialsError as e:
            raise AWSConnectionError("AWS credentials not configured") from e

        except ClientError as e:
            error_message = e.response.get("Error", {}).get("Message", str(e))
            raise AWSConnectionError(f"AWS API error: {error_message}") from e


if __name__ == "__main__":
    config = AWSConfig()
    config.validate_connection()
