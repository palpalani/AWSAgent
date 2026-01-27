"""Core AWS Agentic Agent implementation."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Literal

import anthropic
from botocore.exceptions import ClientError
from dotenv import load_dotenv

from agentic_aws.config import AWSConfig
from agentic_aws.exceptions import AWSConnectionError, ToolExecutionError
from agentic_aws.logging import get_logger
from agentic_aws.models import (
    AWSOperation,
    AWSResourceInput,
    CloudWatchResult,
    OperationProgress,
    OperationResult,
)
from agentic_aws.prompts import ERROR_DIAGNOSIS_PROMPT, SUMMARY_PROMPT, SYSTEM_PROMPT

logger = get_logger(__name__)

if TYPE_CHECKING:
    from mypy_boto3_cloudcontrol import CloudControlApiClient
    from mypy_boto3_logs import CloudWatchLogsClient

load_dotenv()


class AWSAgenticAgent:
    """AI-powered agent for managing AWS infrastructure through natural language."""

    _tools: ClassVar[list[dict[str, Any]] | None] = None

    def __init__(self) -> None:
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.aws_config = AWSConfig()
        self._test_aws_connection()

    def _test_aws_connection(self) -> None:
        """Test AWS connection on initialization."""
        logger.info("Testing AWS connection")

        if not self.aws_config.validate_connection():
            raise AWSConnectionError("AWS connection failed")

        logger.info("AWS connection successful")
        logger.info("Anthropic connection will be tested on first use")

    def _build_system_prompt(self) -> str:
        """Build system prompt for AWS operations."""
        return SYSTEM_PROMPT

    def _format_tools(self) -> list[dict[str, Any]]:
        """Load and cache tool definitions from JSON file."""
        if AWSAgenticAgent._tools is not None:
            return AWSAgenticAgent._tools

        json_path = Path(__file__).parent / "tools.json"
        AWSAgenticAgent._tools = json.loads(json_path.read_text())

        return AWSAgenticAgent._tools

    def _execute_aws_operation(
        self,
        operation: AWSOperation,
        resource_type: str,
        identifier: str | None = None,
        properties: dict[str, Any] | None = None,
        region: str = "us-east-1",
        max_results: int = 20,
        next_token: str | None = None,
    ) -> dict[str, Any]:
        """Execute AWS Cloud Control API operation."""
        try:
            session = self.aws_config.get_session()
            cloudcontrol: CloudControlApiClient = session.client("cloudcontrol", region_name=region)

            logger.info(
                f"Executing {operation} on {resource_type}",
                extra={"extra_data": {"properties": properties, "region": region}},
            )

            if operation == "create":
                return self._handle_create_operation(cloudcontrol, resource_type, properties)

            if operation == "list":
                return self._handle_list_operation(cloudcontrol, resource_type, max_results, next_token)

            if operation == "read" and identifier:
                return self._handle_read_operation(cloudcontrol, resource_type, identifier)

            if operation == "update" and identifier:
                return self._handle_update_operation(cloudcontrol, resource_type, identifier, properties)

            if operation == "delete" and identifier:
                return self._handle_delete_operation(cloudcontrol, resource_type, identifier)

            if operation in ("read", "update", "delete") and not identifier:
                return OperationResult(
                    status="error",
                    operation=operation,
                    resource_type=resource_type,
                    error=f"Operation '{operation}' requires an identifier",
                ).model_dump()

            return OperationResult(
                status="error",
                operation=operation,
                resource_type=resource_type,
                error=f"Unknown operation: {operation}",
            ).model_dump()

        except ClientError as e:
            error_message = e.response.get("Error", {}).get("Message", str(e))
            logger.error(f"AWS Operation Error: {error_message}")
            return OperationResult(
                status="error",
                operation=operation,
                resource_type=resource_type,
                error=f"AWS API error: {error_message}",
                aws_error=str(e),
            ).model_dump()

    def _handle_create_operation(
        self,
        cloudcontrol: CloudControlApiClient,
        resource_type: str,
        properties: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Handle resource creation operation."""
        try:
            response = cloudcontrol.create_resource(
                TypeName=resource_type,
                DesiredState=json.dumps(properties) if properties else "{}",
            )
            logger.debug(f"AWS Response: {response}")

            if "ProgressEvent" not in response:
                return OperationResult(
                    status="error",
                    operation="create",
                    resource_type=resource_type,
                    error="Invalid response from AWS Cloud Control API",
                    aws_response=str(response),
                ).model_dump()

            request_token = response.get("ProgressEvent", {}).get("RequestToken")
            if not request_token:
                return OperationResult(
                    status="error",
                    operation="create",
                    resource_type=resource_type,
                    error="No request token received from AWS",
                    aws_response=str(response),
                ).model_dump()

            return OperationResult(
                status="success",
                operation="create",
                resource_type=resource_type,
                request_token=request_token,
                message=f"Creating {resource_type}...",
                aws_response=str(response),
            ).model_dump()

        except ClientError as e:
            error_message = e.response.get("Error", {}).get("Message", str(e))
            logger.error(f"Create Resource Error: {error_message}")
            return OperationResult(
                status="error",
                operation="create",
                resource_type=resource_type,
                error=f"Failed to create resource: {error_message}",
                aws_error=str(e),
            ).model_dump()

    def _handle_list_operation(
        self,
        cloudcontrol: CloudControlApiClient,
        resource_type: str,
        max_results: int = 20,
        next_token: str | None = None,
    ) -> dict[str, Any]:
        """Handle resource listing operation with pagination."""
        try:
            params: dict[str, Any] = {
                "TypeName": resource_type,
                "MaxResults": min(max_results, 100),
            }
            if next_token:
                params["NextToken"] = next_token

            response = cloudcontrol.list_resources(**params)
            logger.debug(f"List Response: {response}")

            resources = response.get("ResourceDescriptions", [])
            response_next_token = response.get("NextToken")

            return OperationResult(
                status="success",
                operation="list",
                resource_type=resource_type,
                count=len(resources),
                resources=[json.loads(r.get("Properties", "{}")) for r in resources],
                next_token=response_next_token,
                message=f"Retrieved {len(resources)} resources" + (" (more available)" if response_next_token else ""),
                aws_response=str(response),
            ).model_dump()

        except ClientError as e:
            error_message = e.response.get("Error", {}).get("Message", str(e))
            logger.error(f"List Resources Error: {error_message}")
            return OperationResult(
                status="error",
                operation="list",
                resource_type=resource_type,
                error=f"Failed to list resources: {error_message}",
                aws_error=str(e),
            ).model_dump()

    def _handle_read_operation(
        self,
        cloudcontrol: CloudControlApiClient,
        resource_type: str,
        identifier: str,
    ) -> dict[str, Any]:
        """Handle resource read operation."""
        try:
            response = cloudcontrol.get_resource(
                TypeName=resource_type,
                Identifier=identifier,
            )
            logger.debug(f"Read Response: {response}")

            return OperationResult(
                status="success",
                operation="read",
                resource_type=resource_type,
                identifier=identifier,
                properties=json.loads(response["ResourceDescription"]["Properties"]),
                aws_response=str(response),
            ).model_dump()

        except ClientError as e:
            error_message = e.response.get("Error", {}).get("Message", str(e))
            logger.error(f"Read Resource Error: {error_message}")
            return OperationResult(
                status="error",
                operation="read",
                resource_type=resource_type,
                identifier=identifier,
                error=f"Failed to read resource: {error_message}",
                aws_error=str(e),
            ).model_dump()

    def _handle_update_operation(
        self,
        cloudcontrol: CloudControlApiClient,
        resource_type: str,
        identifier: str,
        properties: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Handle resource update operation using patch document."""
        try:
            if not properties:
                return OperationResult(
                    status="error",
                    operation="update",
                    resource_type=resource_type,
                    identifier=identifier,
                    error="Properties are required for update operations",
                ).model_dump()

            patch_document = [{"op": "replace", "path": f"/{key}", "value": value} for key, value in properties.items()]

            response = cloudcontrol.update_resource(
                TypeName=resource_type,
                Identifier=identifier,
                PatchDocument=json.dumps(patch_document),
            )
            logger.debug(f"Update Response: {response}")

            if "ProgressEvent" not in response:
                return OperationResult(
                    status="error",
                    operation="update",
                    resource_type=resource_type,
                    identifier=identifier,
                    error="Invalid response from AWS Cloud Control API",
                    aws_response=str(response),
                ).model_dump()

            request_token = response.get("ProgressEvent", {}).get("RequestToken")

            return OperationResult(
                status="success",
                operation="update",
                resource_type=resource_type,
                identifier=identifier,
                request_token=request_token,
                message=f"Updating {resource_type} ({identifier})...",
                aws_response=str(response),
            ).model_dump()

        except ClientError as e:
            error_message = e.response.get("Error", {}).get("Message", str(e))
            logger.error(f"Update Resource Error: {error_message}")
            return OperationResult(
                status="error",
                operation="update",
                resource_type=resource_type,
                identifier=identifier,
                error=f"Failed to update resource: {error_message}",
                aws_error=str(e),
            ).model_dump()

    def _handle_delete_operation(
        self,
        cloudcontrol: CloudControlApiClient,
        resource_type: str,
        identifier: str,
    ) -> dict[str, Any]:
        """Handle resource deletion operation."""
        try:
            response = cloudcontrol.delete_resource(
                TypeName=resource_type,
                Identifier=identifier,
            )
            logger.debug(f"Delete Response: {response}")

            if "ProgressEvent" not in response:
                return OperationResult(
                    status="error",
                    operation="delete",
                    resource_type=resource_type,
                    identifier=identifier,
                    error="Invalid response from AWS Cloud Control API",
                    aws_response=str(response),
                ).model_dump()

            request_token = response.get("ProgressEvent", {}).get("RequestToken")

            return OperationResult(
                status="success",
                operation="delete",
                resource_type=resource_type,
                identifier=identifier,
                request_token=request_token,
                message=f"Deleting {resource_type} ({identifier})...",
                aws_response=str(response),
            ).model_dump()

        except ClientError as e:
            error_message = e.response.get("Error", {}).get("Message", str(e))
            logger.error(f"Delete Resource Error: {error_message}")
            return OperationResult(
                status="error",
                operation="delete",
                resource_type=resource_type,
                identifier=identifier,
                error=f"Failed to delete resource: {error_message}",
                aws_error=str(e),
            ).model_dump()

    def _poll_operation_status(
        self,
        request_token: str,
        region: str = "us-east-1",
        max_wait_seconds: int = 120,
        initial_delay: float = 2.0,
    ) -> OperationProgress:
        """Poll Cloud Control API for operation completion with exponential backoff.

        Args:
            request_token: The request token from the async operation
            region: AWS region
            max_wait_seconds: Maximum time to wait before returning
            initial_delay: Initial delay between polling attempts

        Returns:
            OperationProgress with current status
        """
        session = self.aws_config.get_session()
        cloudcontrol: CloudControlApiClient = session.client("cloudcontrol", region_name=region)

        delay = initial_delay
        max_delay = 30.0
        elapsed = 0.0

        while elapsed < max_wait_seconds:
            try:
                response = cloudcontrol.get_resource_request_status(RequestToken=request_token)
                progress_event = response.get("ProgressEvent", {})
                operation_status: Literal[
                    "PENDING", "IN_PROGRESS", "SUCCESS", "FAILED", "CANCEL_IN_PROGRESS", "CANCEL_COMPLETE"
                ] = progress_event.get("OperationStatus", "PENDING")

                logger.info(
                    f"Operation status: {operation_status}",
                    extra={"extra_data": {"request_token": request_token}},
                )

                if operation_status in ("SUCCESS", "FAILED", "CANCEL_COMPLETE"):
                    return OperationProgress(
                        request_token=request_token,
                        operation_status=operation_status,
                        resource_type=progress_event.get("TypeName", ""),
                        identifier=progress_event.get("Identifier"),
                        status_message=progress_event.get("StatusMessage"),
                        error_code=progress_event.get("ErrorCode"),
                    )

                time.sleep(delay)
                elapsed += delay
                delay = min(delay * 1.5, max_delay)

            except ClientError as e:
                error_message = e.response.get("Error", {}).get("Message", str(e))
                logger.error(f"Error polling operation status: {error_message}")
                return OperationProgress(
                    request_token=request_token,
                    operation_status="FAILED",
                    resource_type="",
                    status_message=f"Failed to poll status: {error_message}",
                    error_code=e.response.get("Error", {}).get("Code"),
                )

        return OperationProgress(
            request_token=request_token,
            operation_status="IN_PROGRESS",
            resource_type="",
            status_message=f"Operation still in progress after {max_wait_seconds}s",
            retry_after=int(delay),
        )

    def _query_cloudwatch_logs(self, function_name: str, hours_back: int = 1) -> dict[str, Any]:
        """Query CloudWatch Logs for Lambda function errors."""
        try:
            session = self.aws_config.get_session()
            logs_client: CloudWatchLogsClient = session.client("logs")

            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours_back)

            log_group_name = f"/aws/lambda/{function_name}"

            response = logs_client.filter_log_events(
                logGroupName=log_group_name,
                startTime=int(start_time.timestamp() * 1000),
                endTime=int(end_time.timestamp() * 1000),
                filterPattern="ERROR",
            )

            error_logs = [
                {
                    "timestamp": datetime.fromtimestamp(event["timestamp"] / 1000).isoformat(),
                    "message": event["message"],
                    "logStreamName": event["logStreamName"],
                }
                for event in response.get("events", [])
            ]

            return CloudWatchResult(
                status="success",
                function_name=function_name,
                hours_back=hours_back,
                error_count=len(error_logs),
                error_logs=error_logs[:10],
            ).model_dump()

        except ClientError as e:
            error_message = e.response.get("Error", {}).get("Message", str(e))
            return CloudWatchResult(
                status="error",
                function_name=function_name,
                error=error_message,
            ).model_dump()

    def _diagnose_error(
        self,
        operation: str,
        resource_type: str,
        error_message: str,
        error_code: str | None = None,
    ) -> str:
        """Diagnose an AWS error and provide user-friendly guidance.

        Args:
            operation: The operation that failed
            resource_type: The AWS resource type
            error_message: The error message from AWS
            error_code: The error code from AWS (optional)

        Returns:
            User-friendly diagnosis and recommendations
        """
        try:
            diagnosis_prompt = ERROR_DIAGNOSIS_PROMPT.format(
                operation=operation,
                resource_type=resource_type,
                error_message=error_message,
                error_code=error_code or "Not provided",
            )

            response = self.client.messages.create(
                model="claude-3-5-sonnet-latest",
                max_tokens=500,
                messages=[{"role": "user", "content": diagnosis_prompt}],
            )

            return response.content[0].text  # type: ignore[union-attr]

        except (anthropic.APIConnectionError, anthropic.APIStatusError) as e:
            logger.warning(f"Failed to diagnose error: {e}")
            return f"Error: {error_message}"

    def _generate_summary(self, tool_name: str, tool_result: dict[str, Any], user_question: str) -> str:
        """Generate natural language summary from tool results."""
        if tool_result.get("status") == "error":
            return self._diagnose_error(
                operation=tool_result.get("operation", "unknown"),
                resource_type=tool_result.get("resource_type", "unknown"),
                error_message=tool_result.get("error", "Unknown error"),
                error_code=tool_result.get("aws_error"),
            )

        try:
            summary_prompt = SUMMARY_PROMPT.format(
                tool_name=tool_name,
                tool_result=json.dumps(tool_result, indent=2),
                user_question=user_question,
            )

            response = self.client.messages.create(
                model="claude-3-5-sonnet-latest",
                max_tokens=500,
                messages=[{"role": "user", "content": summary_prompt}],
            )

            return response.content[0].text  # type: ignore[union-attr]

        except anthropic.APIConnectionError as e:
            raise ToolExecutionError(f"Failed to connect to Anthropic API: {e}") from e
        except anthropic.APIStatusError as e:
            raise ToolExecutionError(f"Anthropic API error: {e.message}") from e

    def _execute_tool(self, tool_name: str, tool_input: dict[str, Any], user_input: str) -> tuple[dict[str, Any], str]:
        """Execute a tool and return the result and formatted output.

        Returns:
            Tuple of (tool_result_dict, formatted_response_content)
        """
        if tool_name == "aws_cloud_control":
            try:
                validated_input = AWSResourceInput(**tool_input)
                result = self._execute_aws_operation(
                    operation=validated_input.operation,
                    resource_type=validated_input.resource_type,
                    identifier=validated_input.identifier,
                    properties=validated_input.properties,
                    region=validated_input.region,
                    max_results=validated_input.max_results,
                    next_token=validated_input.next_token,
                )
            except ValueError as e:
                result = OperationResult(
                    status="error",
                    operation=tool_input.get("operation", "unknown"),
                    resource_type=tool_input.get("resource_type", "unknown"),
                    error=f"Validation error: {e}",
                ).model_dump()
            summary = self._generate_summary(tool_name, result, user_input)
            return result, f"\n\nAI Summary:\n{summary}"

        if tool_name == "cloudwatch_logs":
            result = self._query_cloudwatch_logs(**tool_input)
            summary = self._generate_summary(tool_name, result, user_input)
            return result, f"\n\nCloudWatch Logs Result:\n{json.dumps(result, indent=2)}\n\nAI Summary:\n{summary}"

        return {"error": f"Unknown tool: {tool_name}"}, f"\n\nError: Unknown tool '{tool_name}'"

    def process_request(
        self,
        user_input: str,
        history: list[dict[str, str]],
        max_iterations: int = 10,
    ) -> str:
        """Process a user request using an agentic loop until completion.

        Args:
            user_input: The user's message
            history: Conversation history (modified in place)
            max_iterations: Maximum number of agent turns before stopping

        Returns:
            The agent's final response
        """
        history.append({"role": "user", "content": user_input})
        final_response = ""
        iteration = 0

        try:
            while iteration < max_iterations:
                iteration += 1
                logger.info(f"Agent iteration {iteration}/{max_iterations}")

                response = self.client.messages.create(
                    model="claude-3-5-sonnet-latest",
                    max_tokens=2000,
                    system=self._build_system_prompt(),
                    messages=history,  # type: ignore[arg-type]
                    tools=self._format_tools(),  # type: ignore[arg-type]
                )

                assistant_content: list[dict[str, Any]] = []
                tool_results: list[dict[str, Any]] = []
                response_text = ""

                for content_block in response.content:
                    if content_block.type == "text":
                        logger.debug("Received TEXT response from LLM")
                        response_text += content_block.text
                        assistant_content.append(
                            {
                                "type": "text",
                                "text": content_block.text,
                            }
                        )

                    elif content_block.type == "tool_use":
                        logger.info(
                            f"Received tool use request: {content_block.name}",
                            extra={"extra_data": {"tool_input": content_block.input}},
                        )

                        tool_input: dict[str, Any] = content_block.input
                        result, formatted_output = self._execute_tool(content_block.name, tool_input, user_input)
                        response_text += formatted_output

                        assistant_content.append(
                            {
                                "type": "tool_use",
                                "id": content_block.id,
                                "name": content_block.name,
                                "input": content_block.input,
                            }
                        )

                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": content_block.id,
                                "content": json.dumps(result),
                            }
                        )

                history.append({"role": "assistant", "content": assistant_content})  # type: ignore[dict-item]

                if tool_results:
                    history.append({"role": "user", "content": tool_results})  # type: ignore[dict-item]

                final_response = response_text

                if response.stop_reason == "end_turn":
                    logger.info("Agent completed (stop_reason: end_turn)")
                    break

                if response.stop_reason != "tool_use":
                    logger.info(f"Agent stopped (stop_reason: {response.stop_reason})")
                    break

            if iteration >= max_iterations:
                logger.warning(f"Agent reached max iterations ({max_iterations})")
                final_response += "\n\n(Note: Maximum processing steps reached)"

            return final_response

        except anthropic.APIConnectionError as e:
            error_msg = f"Error: Failed to connect to Anthropic API: {e}"
            logger.error(error_msg)
            return error_msg
        except anthropic.APIStatusError as e:
            error_msg = f"Error: Anthropic API error: {e.message}"
            logger.error(error_msg)
            return error_msg
