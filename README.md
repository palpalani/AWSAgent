# Agentic AWS

AI-powered AWS infrastructure management through natural language conversations. Chat with an AI agent to create, list, read, and manage AWS resources using the AWS Cloud Control API.

## Key Features

- **Natural Language Interface** - Describe what you want in plain English, the AI handles the AWS API calls
- **AWS Cloud Control API** - Unified API for managing 1000+ AWS resource types (S3, EC2, RDS, Lambda, etc.)
- **CloudWatch Logs Integration** - Query Lambda function error logs through conversation
- **Conversational Context** - Maintains chat history for multi-turn interactions
- **Safety First** - Agent always asks for confirmation before creating resources

---

## Table of Contents

- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
- [Architecture](#architecture)
- [Environment Variables](#environment-variables)
- [Available Commands](#available-commands)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| **Language** | Python 3.11+ |
| **Package Manager** | [uv](https://docs.astral.sh/uv/) |
| **AI Model** | Claude 3.5 Sonnet (Anthropic) |
| **Backend** | FastAPI |
| **Frontend** | Streamlit |
| **AWS SDK** | boto3 with Cloud Control API |
| **HTTP Client** | httpx |
| **Validation** | Pydantic v2 |
| **Type Checking** | mypy (strict mode) |
| **Linting/Formatting** | ruff |
| **Testing** | pytest |

---

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.11 or higher**
  ```bash
  python --version  # Should be 3.11+
  ```

- **uv** (Python package manager)
  ```bash
  # Install uv
  curl -LsSf https://astral.sh/uv/install.sh | sh

  # Verify installation
  uv --version
  ```

- **AWS Account** with programmatic access (Access Key ID and Secret Access Key)

- **Anthropic API Key** from [console.anthropic.com](https://console.anthropic.com/)

---

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/agentic-aws-resource-management.git
cd agentic-aws-resource-management
```

### 2. Install Dependencies

uv automatically creates a virtual environment and installs all dependencies:

```bash
uv sync --all-extras
```

This installs both runtime dependencies and development tools (pytest, mypy, ruff).

### 3. Configure Environment Variables

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your actual values:

```bash
# Required - Get from https://console.anthropic.com/
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx

# Required - AWS IAM user credentials with Cloud Control API permissions
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_DEFAULT_REGION=us-east-1

# Optional - Backend URL (default: http://localhost:8000)
API_URL=http://localhost:8000
```

### 4. Verify AWS Connection

Test that your AWS credentials are configured correctly:

```bash
uv run python -c "from agentic_aws.config import AWSConfig; AWSConfig().validate_connection()"
```

Expected output:
```
AWS Connection successful! Account: 123456789012
```

### 5. Start the Application

You need to run both the FastAPI backend and the Streamlit frontend:

**Terminal 1 - Start the API server:**
```bash
uv run uvicorn main:app --reload --port 8000
```

**Terminal 2 - Start the Streamlit chat interface:**
```bash
uv run streamlit run chat.py --server.port 8501
```

### 6. Open the Chat Interface

Navigate to [http://localhost:8501](http://localhost:8501) in your browser.

Try these example prompts:
- "List all my S3 buckets"
- "Show me my EC2 instances"
- "Check errors in my Lambda function named my-function"

---

## Architecture

### High-Level Data Flow

```
┌─────────────────┐     HTTP POST      ┌─────────────────┐
│   Streamlit     │ ──────────────────▶│    FastAPI      │
│   (chat.py)     │                    │   (main.py)     │
│   Port 8501     │◀────────────────── │   Port 8000     │
└─────────────────┘     JSON Response  └────────┬────────┘
                                                │
                                                ▼
                                       ┌─────────────────┐
                                       │   Processor     │
                                       │ (processor.py)  │
                                       │   Singleton     │
                                       └────────┬────────┘
                                                │
                                                ▼
                                       ┌─────────────────┐
                                       │  AWSAgenticAgent│
                                       │   (agent.py)    │
                                       └────────┬────────┘
                                                │
                    ┌───────────────────────────┼───────────────────────────┐
                    │                           │                           │
                    ▼                           ▼                           ▼
           ┌─────────────────┐        ┌─────────────────┐        ┌─────────────────┐
           │  Anthropic API  │        │  AWS Cloud      │        │  AWS CloudWatch │
           │  (Claude 3.5)   │        │  Control API    │        │     Logs        │
           └─────────────────┘        └─────────────────┘        └─────────────────┘
```

### Directory Structure

```
agentic-aws-resource-management/
├── src/
│   └── agentic_aws/
│       ├── __init__.py          # Package exports
│       ├── agent.py             # Core AI agent with tool execution
│       ├── cli.py               # CLI entry points
│       ├── config.py            # AWS session management
│       ├── exceptions.py        # Custom exception classes
│       ├── models.py            # Pydantic request/response models
│       ├── processor.py         # Request processor (singleton pattern)
│       ├── prompts.py           # System prompts for Claude
│       └── tools.json           # Tool definitions for Claude function calling
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Shared pytest fixtures
│   ├── test_agent.py            # Agent unit tests
│   └── test_config.py           # AWS config tests
├── main.py                      # FastAPI application
├── chat.py                      # Streamlit frontend
├── pyproject.toml               # Project configuration (uv/hatch)
├── uv.lock                      # Dependency lock file
├── .env.example                 # Environment template
├── CLAUDE.md                    # AI assistant instructions
└── README.md                    # This file
```

### Key Components

#### `AWSAgenticAgent` (src/agentic_aws/agent.py)

The core agent class that:
1. Receives user messages and conversation history
2. Sends requests to Claude 3.5 Sonnet with tool definitions
3. Executes AWS operations when Claude requests tool use
4. Generates natural language summaries of operation results

```python
class AWSAgenticAgent:
    def process_request(self, user_input: str, history: list[dict]) -> str:
        # 1. Send message to Claude with tools
        # 2. Handle tool_use responses by executing AWS operations
        # 3. Generate summary and return response
```

#### Tool Definitions (src/agentic_aws/tools.json)

Two tools available to the AI agent:

| Tool | Description | Operations |
|------|-------------|------------|
| `aws_cloud_control` | AWS Cloud Control API operations | create, read, update, delete, list |
| `cloudwatch_logs` | Query CloudWatch Logs | Filter Lambda function errors |

#### Request Flow

1. **User Input** → Streamlit sends POST to `/chat` endpoint
2. **FastAPI** → Validates request with Pydantic, calls `process_request()`
3. **Processor** → Uses singleton pattern to reuse agent instance
4. **Agent** → Sends message to Claude API with tool definitions
5. **Claude** → Returns either text response or tool_use request
6. **Tool Execution** → Agent executes AWS API call if tool requested
7. **Summary** → Agent uses Claude to summarize results in natural language
8. **Response** → JSON response with message and updated history

### Pydantic Models

```python
# Request from Streamlit to FastAPI
class ChatRequest(BaseModel):
    message: str              # User's message
    history: list[ChatMessage]  # Conversation history

# Response from FastAPI to Streamlit
class ChatResponse(BaseModel):
    response: str                    # Agent's response text
    updated_history: list[ChatMessage]  # Updated conversation

# AWS operation result
class OperationResult(BaseModel):
    status: Literal["success", "error"]
    operation: Literal["create", "read", "update", "delete", "list"]
    resource_type: str        # e.g., "AWS::S3::Bucket"
    # ... additional fields for resources, errors, etc.
```

---

## Environment Variables

### Required Variables

| Variable | Description | How to Get |
|----------|-------------|------------|
| `ANTHROPIC_API_KEY` | Claude API key for AI interactions | [console.anthropic.com](https://console.anthropic.com/) |
| `AWS_ACCESS_KEY_ID` | AWS access key | AWS IAM Console → Users → Security credentials |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | Created with access key |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_DEFAULT_REGION` | AWS region for operations | `us-east-1` |
| `API_URL` | Backend URL for Streamlit | `http://localhost:8000` |

### AWS IAM Permissions

Your AWS user needs permissions for Cloud Control API. Minimal policy:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "cloudcontrol:CreateResource",
                "cloudcontrol:DeleteResource",
                "cloudcontrol:GetResource",
                "cloudcontrol:ListResources",
                "cloudcontrol:UpdateResource",
                "cloudformation:*"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:FilterLogEvents",
                "logs:DescribeLogGroups",
                "logs:DescribeLogStreams"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "sts:GetCallerIdentity"
            ],
            "Resource": "*"
        }
    ]
}
```

---

## Available Commands

### Development

| Command | Description |
|---------|-------------|
| `uv sync --all-extras` | Install all dependencies |
| `uv run uvicorn main:app --reload --port 8000` | Start FastAPI server with auto-reload |
| `uv run streamlit run chat.py --server.port 8501` | Start Streamlit frontend |
| `uv run pytest` | Run test suite |
| `uv run pytest --cov=src` | Run tests with coverage report |
| `uv run ruff check src tests main.py chat.py` | Run linter |
| `uv run ruff format src tests main.py chat.py` | Format code |
| `uv run mypy src` | Run type checker |

### CLI Entry Points

After installation, you can also use the CLI commands:

```bash
uv run agentic-aws-api   # Start FastAPI server
uv run agentic-aws-chat  # Start Streamlit chat
```

---

## API Reference

### Health Check

```http
GET /
```

**Response:**
```json
{
    "message": "FastAPI is running"
}
```

### Chat Endpoint

```http
POST /chat
Content-Type: application/json
```

**Request Body:**
```json
{
    "message": "List all my S3 buckets",
    "history": [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi! How can I help?"}
    ]
}
```

**Response:**
```json
{
    "response": "I found 3 S3 buckets in your account:\n\n1. my-bucket-1\n2. my-bucket-2\n3. my-bucket-3",
    "updated_history": [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi! How can I help?"},
        {"role": "user", "content": "List all my S3 buckets"},
        {"role": "assistant", "content": "I found 3 S3 buckets..."}
    ]
}
```

### Interactive API Docs

When the server is running, access the OpenAPI documentation:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## Testing

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_agent.py

# Run specific test
uv run pytest tests/test_agent.py::TestAWSAgenticAgent::test_agent_initialization

# Run with coverage
uv run pytest --cov=src --cov-report=html
```

### Test Structure

```
tests/
├── conftest.py         # Shared fixtures
│   ├── mock_aws_session      # Mocked boto3 session
│   ├── mock_anthropic_client # Mocked Claude client
│   ├── mock_environment      # Environment variables
│   └── sample_chat_history   # Test conversation
├── test_agent.py       # Agent unit tests
│   ├── test_agent_initialization
│   ├── test_format_tools_returns_list
│   ├── test_execute_aws_operation_*
│   ├── test_process_request_text_response
│   └── test_query_cloudwatch_logs_success
└── test_config.py      # AWS config tests
    ├── test_init_loads_environment_variables
    ├── test_get_session_returns_boto3_session
    └── test_validate_connection_*
```

### Writing Tests

Tests use mocking to avoid actual AWS/Anthropic API calls:

```python
def test_execute_aws_operation_list_success(
    self,
    agent: AWSAgenticAgent,
) -> None:
    """Test successful list operation."""
    mock_cloudcontrol = MagicMock()
    mock_cloudcontrol.list_resources.return_value = {
        "ResourceDescriptions": [
            {"Properties": json.dumps({"BucketName": "test-bucket"})}
        ]
    }

    with patch.object(agent.aws_config, "get_session") as mock_session:
        mock_session.return_value.client.return_value = mock_cloudcontrol
        result = agent._execute_aws_operation(
            operation="list",
            resource_type="AWS::S3::Bucket",
        )

    assert result["status"] == "success"
    assert result["count"] == 1
```

---

## Troubleshooting

### AWS Connection Failed

**Error:** `AWSConnectionError: AWS credentials not configured`

**Solutions:**
1. Verify `.env` file exists and contains valid credentials
2. Check environment variables are set:
   ```bash
   echo $AWS_ACCESS_KEY_ID
   ```
3. Test credentials directly:
   ```bash
   aws sts get-caller-identity
   ```

### Anthropic API Error

**Error:** `Error: Anthropic API error: ...`

**Solutions:**
1. Verify `ANTHROPIC_API_KEY` is set correctly
2. Check API key hasn't expired at [console.anthropic.com](https://console.anthropic.com/)
3. Ensure you have API credits available

### Port Already in Use

**Error:** `Address already in use`

**Solutions:**
```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use different ports
uv run uvicorn main:app --port 8001
uv run streamlit run chat.py --server.port 8502
```

### Module Not Found

**Error:** `ModuleNotFoundError: No module named 'agentic_aws'`

**Solutions:**
```bash
# Ensure dependencies are installed
uv sync --all-extras

# Verify you're using uv run
uv run python -c "import agentic_aws"
```

### Cloud Control API Errors

**Error:** `UnsupportedActionException`

**Cause:** Not all AWS resources support Cloud Control API.

**Solution:** Check [supported resources](https://docs.aws.amazon.com/cloudcontrolapi/latest/userguide/supported-resources.html).

### Resource Creation is Asynchronous

**Issue:** Resource shows "success" but doesn't appear immediately in AWS Console.

**Cause:** Cloud Control API is asynchronous. The API returns a request token immediately.

**Solution:** Check resource status using the request token:
```bash
aws cloudcontrol get-resource-request-status --request-token YOUR_TOKEN
```

### Streamlit Connection Error

**Error:** `Error communicating with backend`

**Solutions:**
1. Ensure FastAPI server is running on port 8000
2. Check `API_URL` environment variable
3. Verify no firewall blocking localhost connections

---

## Supported AWS Resources

The AWS Cloud Control API supports 1000+ resource types. Common examples:

| Resource Type | Operations |
|--------------|------------|
| `AWS::S3::Bucket` | create, read, list, delete |
| `AWS::EC2::Instance` | create, read, list, delete |
| `AWS::RDS::DBInstance` | create, read, list, delete |
| `AWS::Lambda::Function` | create, read, list, delete |
| `AWS::DynamoDB::Table` | create, read, list, delete |
| `AWS::SQS::Queue` | create, read, list, delete |

See full list: [AWS Cloud Control Supported Resources](https://docs.aws.amazon.com/cloudcontrolapi/latest/userguide/supported-resources.html)

---

## Usage Examples

### Infrastructure Management

```
User: "Create an S3 bucket for my photos"
AI: I'll help you create an S3 bucket for your photos. I need a few details first:
    1. What would you like to name the bucket? (must be globally unique)
    2. What type of encryption would you prefer? (AES-256 or KMS)
    3. Should I enable versioning?

User: "Name it my-photo-bucket-2024, use AES-256, and enable versioning"
AI: ✅ Successfully created S3 bucket 'my-photo-bucket-2024' with:
    - Server-side encryption: AES-256
    - Versioning: Enabled
```

### Monitoring & Debugging

```
User: "Check for errors in my lambda function 'user-authentication'"
AI: I found 3 errors in the last hour:
    - 2024-01-15 10:23:45: Authentication failed for user 'john@example.com'
    - 2024-01-15 10:45:12: Invalid token format detected
    - 2024-01-15 11:02:33: Database connection timeout
```

### Resource Listing

```
User: "Show me all my S3 buckets"
AI: You have 5 S3 buckets in us-east-1:
    1. my-photo-bucket-2024
    2. data-backup-bucket
    3. static-website-assets
    4. logs-archive
    5. terraform-state
```

---

## Security Considerations

### Current Setup (Development)
- Uses AWS access keys stored in `.env` file
- Not recommended for production use

### Production Recommendations
1. **Use IAM Roles** instead of access keys
2. **Implement AWS SSO** for user authentication
3. **Use least privilege** permissions
4. **Enable CloudTrail** for audit logging
5. **Store secrets in AWS Secrets Manager** or similar

---

## License

MIT License - see [LICENSE](LICENSE) for details.
