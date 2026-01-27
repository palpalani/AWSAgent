"""Pydantic models for request/response validation."""

import re
from typing import Annotated, Any, Literal, TypeAlias

from pydantic import BaseModel, Field, field_validator

MessageRole: TypeAlias = Literal["user", "assistant"]
OperationStatus: TypeAlias = Literal["success", "error"]
AWSOperation: TypeAlias = Literal["create", "read", "update", "delete", "list"]

AWS_RESOURCE_TYPE_PATTERN = re.compile(r"^AWS::[A-Za-z0-9]+::[A-Za-z0-9]+$")
SAFE_IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z0-9_\-:./]+$")


class ChatMessage(BaseModel):
    """A single message in the conversation history."""

    model_config = {"str_strip_whitespace": True}

    role: MessageRole = Field(description="Message role: 'user' or 'assistant'")
    content: str = Field(description="Message content", max_length=50000)


class ChatRequest(BaseModel):
    """Request model for the chat endpoint."""

    model_config = {"str_strip_whitespace": True}

    message: str = Field(min_length=1, max_length=10000, description="User message to process")
    history: list[ChatMessage] = Field(
        default_factory=list,
        description="Conversation history",
        max_length=100,
    )


class AWSResourceInput(BaseModel):
    """Validated input for AWS operations."""

    model_config = {"str_strip_whitespace": True}

    operation: AWSOperation = Field(description="The operation to perform")
    resource_type: Annotated[str, Field(min_length=5, max_length=100)] = Field(
        description="AWS resource type (e.g., AWS::S3::Bucket)"
    )
    identifier: Annotated[str | None, Field(max_length=2048)] = Field(default=None, description="Resource identifier")
    properties: dict[str, Any] | None = Field(default=None, description="Resource properties")
    region: str = Field(default="us-east-1", description="AWS region")
    max_results: Annotated[int, Field(ge=1, le=100)] = Field(
        default=20, description="Maximum number of results for list operations"
    )
    next_token: str | None = Field(default=None, description="Pagination token for list operations")

    @field_validator("resource_type")
    @classmethod
    def validate_resource_type(cls, v: str) -> str:
        if not AWS_RESOURCE_TYPE_PATTERN.match(v):
            raise ValueError(f"Invalid AWS resource type format: {v}. Expected format: AWS::Service::Resource")
        return v

    @field_validator("identifier")
    @classmethod
    def validate_identifier(cls, v: str | None) -> str | None:
        if v is not None and not SAFE_IDENTIFIER_PATTERN.match(v):
            raise ValueError(
                f"Invalid identifier format: {v}. "
                "Only alphanumeric characters, underscores, hyphens, colons, slashes, and dots allowed."
            )
        return v

    @field_validator("region")
    @classmethod
    def validate_region(cls, v: str) -> str:
        valid_regions = [
            "us-east-1",
            "us-east-2",
            "us-west-1",
            "us-west-2",
            "eu-west-1",
            "eu-west-2",
            "eu-west-3",
            "eu-central-1",
            "eu-north-1",
            "ap-northeast-1",
            "ap-northeast-2",
            "ap-northeast-3",
            "ap-southeast-1",
            "ap-southeast-2",
            "ap-south-1",
            "sa-east-1",
            "ca-central-1",
            "me-south-1",
            "af-south-1",
        ]
        if v not in valid_regions:
            raise ValueError(f"Invalid AWS region: {v}")
        return v


class ChatResponse(BaseModel):
    """Response model for the chat endpoint."""

    response: str = Field(description="Agent response text")
    updated_history: list[ChatMessage] = Field(description="Updated conversation history")


class OperationResult(BaseModel):
    """Result of an AWS Cloud Control operation."""

    status: OperationStatus = Field(description="Operation status: 'success' or 'error'")
    operation: AWSOperation = Field(description="Operation type performed")
    resource_type: str = Field(description="AWS resource type")
    identifier: str | None = Field(default=None, description="Resource identifier")
    request_token: str | None = Field(default=None, description="AWS request token for async operations")
    message: str | None = Field(default=None, description="Status message")
    count: int | None = Field(default=None, description="Resource count for list operations")
    total_count: int | None = Field(default=None, description="Total count of resources (if pagination)")
    resources: list[dict[str, Any]] | None = Field(default=None, description="List of resources")
    properties: dict[str, Any] | None = Field(default=None, description="Resource properties")
    next_token: str | None = Field(default=None, description="Pagination token for next page")
    error: str | None = Field(default=None, description="Error message if failed")
    aws_response: str | None = Field(default=None, description="Raw AWS response")
    aws_error: str | None = Field(default=None, description="AWS error details")


class CloudWatchResult(BaseModel):
    """Result of a CloudWatch Logs query."""

    status: OperationStatus = Field(description="Query status: 'success' or 'error'")
    function_name: str = Field(description="Lambda function name queried")
    hours_back: int | None = Field(default=None, description="Hours of logs queried")
    error_count: int | None = Field(default=None, description="Number of errors found")
    error_logs: list[dict[str, Any]] | None = Field(default=None, description="Error log entries")
    error: str | None = Field(default=None, description="Error message if query failed")


OperationProgressStatus: TypeAlias = Literal[
    "PENDING", "IN_PROGRESS", "SUCCESS", "FAILED", "CANCEL_IN_PROGRESS", "CANCEL_COMPLETE"
]


class OperationProgress(BaseModel):
    """Progress status for async Cloud Control API operations."""

    request_token: str = Field(description="AWS request token for the operation")
    operation_status: OperationProgressStatus = Field(description="Current status of the operation")
    resource_type: str = Field(description="AWS resource type")
    identifier: str | None = Field(default=None, description="Resource identifier if available")
    status_message: str | None = Field(default=None, description="Status message from AWS")
    error_code: str | None = Field(default=None, description="Error code if failed")
    retry_after: int | None = Field(default=None, description="Suggested retry delay in seconds")
