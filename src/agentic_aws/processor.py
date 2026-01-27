"""Request processor with singleton agent pattern."""

from functools import lru_cache

from agentic_aws.agent import AWSAgenticAgent


@lru_cache(maxsize=1)
def get_agent() -> AWSAgenticAgent:
    """Get or create the singleton agent instance."""
    return AWSAgenticAgent()


def process_request(user_message: str, history: list[dict[str, str]]) -> str:
    """Process a user request using the singleton agent."""
    agent = get_agent()
    return agent.process_request(user_message, history=history)
