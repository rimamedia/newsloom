import json
import logging
import os
from datetime import timedelta
from typing import Dict, List, Optional, Tuple

import boto3
from agents.models import Agent
from django.utils import timezone
from dotenv import load_dotenv
from mediamanager.models import Examples
from sources.models import Doc, News

# Load environment variables from .env file
load_dotenv()


logger = logging.getLogger(__name__)


def validate_aws_credentials() -> Tuple[bool, Optional[str]]:
    """
    Validate AWS credentials are properly configured.

    Returns:
        Tuple of (is_valid, error_message)
    """
    required_vars = [
        "BEDROCK_AWS_ACCESS_KEY_ID",
        "BEDROCK_AWS_SECRET_ACCESS_KEY",
        "BEDROCK_AWS_REGION",
    ]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        return (
            False,
            f"Missing required AWS environment variables: {', '.join(missing_vars)}",
        )

    return True, None


def get_bedrock_client():
    """
    Get a boto3 client for Amazon Bedrock.

    Returns:
        boto3 client for bedrock-runtime

    Raises:
        ValueError: If AWS credentials are not properly configured
    """
    # Validate credentials before creating client
    is_valid, error_msg = validate_aws_credentials()
    if not is_valid:
        logger.error("AWS credentials validation failed: %s", error_msg)
        raise ValueError(f"AWS credentials not properly configured: {error_msg}")

    try:
        session = boto3.Session(
            aws_access_key_id=os.getenv("BEDROCK_AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("BEDROCK_AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("BEDROCK_AWS_REGION", "us-east-1"),
        )

        client = session.client(
            service_name="bedrock-runtime",
            region_name=os.getenv("BEDROCK_AWS_REGION", "us-east-1"),
        )
        return client

    except Exception as e:
        error_msg = f"Failed to initialize Bedrock client: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg)


def validate_prompt_template(
    template: str, available_vars: Dict[str, str]
) -> List[str]:
    """
    Validate that all variables in the template exist in available_vars.

    Args:
        template: The prompt template string
        available_vars: Dictionary of available variables

    Returns:
        List of missing variables if any
    """
    try:
        # Test format the template with a dict comprehension of all possible variables
        test_vars = {key: "{" + key + "}" for key in available_vars.keys()}
        template.format(**test_vars)
        return []
    except KeyError as e:
        # Extract the missing key from the KeyError message
        missing_key = str(e).strip("'")
        return [missing_key]


def invoke_bedrock_anthropic(system_prompt: str, user_prompt: str, client=None) -> Dict:
    """
    Invoke the Anthropic model through Amazon Bedrock with tool calling.

    Args:
        system_prompt: The system prompt that defines behavior
        user_prompt: The user prompt with content to process
        client: Optional pre-configured boto3 client

    Returns:
        Dict containing the model's response
    """
    try:
        if client is None:
            client = get_bedrock_client()

        # Define the create_docs tool
        tools = [
            {
                "name": "create_docs",
                "description": "Create a list of docs from the analyzed news content",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "topic": {
                            "type": "string",
                            "description": "The main topic or theme of the posts",
                        },
                        "docs": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "text": {
                                        "type": "string",
                                        "description": "The text content of the docs",
                                    },
                                    "url": {
                                        "type": "string",
                                        "description": "The source URL for the docs",
                                    },
                                },
                                "required": ["text", "url"],
                            },
                            "description": "Array of docs to create",
                        },
                    },
                    "required": ["topic", "docs"],
                },
            }
        ]

        logger.info(
            "Preparing Bedrock request with tools: %s", json.dumps(tools, indent=2)
        )

        # Initialize messages list
        messages = [
            {"role": "user", "content": [{"type": "text", "text": user_prompt}]}
        ]
        final_response = None

        while True:
            # Prepare request body
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 8192,
                "temperature": 0,
                "messages": messages,
                "system": system_prompt,
                "tools": tools,
            }

            logger.debug(
                "Sending request to Bedrock with body: %s", json.dumps(request_body)
            )

            # Make API call
            response = client.invoke_model(
                modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
                contentType="application/json",
                accept="application/json",
                body=json.dumps(request_body),
            )

            # Parse response
            response_body = json.loads(response["body"].read())
            logger.info(
                "Received raw response from Bedrock: %s",
                json.dumps(response_body, indent=2),
            )

            # Add assistant's response to messages
            messages.append(
                {"role": "assistant", "content": response_body.get("content", [])}
            )

            # Get text content for final response
            text_content = ""
            for block in response_body.get("content", []):
                if block.get("type") == "text":
                    text_content += block.get("text", "")
            final_response = text_content.strip()

            # Check for tool use
            tool_calls = [
                c
                for c in response_body.get("content", [])
                if c.get("type") == "tool_use"
            ]

            if not tool_calls:
                logger.info("No tool calls in response, completing conversation")
                break

            # Process tool calls
            for content in tool_calls:
                logger.info(f"Processing tool call: {content.get('name')}")
                try:
                    if content.get("name") == "create_docs":
                        tool_input = content.get("input", {})
                        logger.info(
                            "Successfully extracted tool input: %s",
                            json.dumps(tool_input, indent=2),
                        )
                        # Add tool result to messages
                        messages.append(
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "tool_result",
                                        "tool_use_id": content.get("id"),
                                        "content": json.dumps(tool_input),
                                    }
                                ],
                            }
                        )
                except Exception as e:
                    error_msg = f"Error executing tool {content.get('name')}: {str(e)}"
                    logger.error(error_msg)
                    messages.append(
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": content.get("id"),
                                    "content": f"Error executing tool: {str(e)}",
                                }
                            ],
                        }
                    )

        return {
            "completion": final_response,
            "full_response": response_body,
            "message_history": messages,
        }

    except Exception as e:
        error_msg = f"Unexpected error in invoke_bedrock_anthropic: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise ValueError(error_msg)


def process_news_stream(
    stream_id: int,
    agent_id: int,
    time_window_minutes: int = 60,
    max_items: int = 100,
    save_to_docs: bool = True,
) -> Dict:
    """
    Process news items using the specified agent.

    Args:
        stream_id: ID of the stream
        agent_id: ID of the agent to use
        time_window_minutes: Time window in minutes to look back for news
        max_items: Maximum number of news items to process
        save_to_docs: Whether to save the processed output to docs

    Returns:
        Dict containing processing results
    """
    from streams.models import Stream

    try:
        logger.info(
            "Starting news stream processing for stream_id=%d, agent_id=%d",
            stream_id,
            agent_id,
        )

        # Validate AWS credentials first
        is_valid, error_msg = validate_aws_credentials()
        if not is_valid:
            raise ValueError(f"AWS credentials validation failed: {error_msg}")

        # Get the stream and agent
        stream = Stream.objects.get(id=stream_id)
        agent = Agent.objects.get(id=agent_id)

        if not agent.is_active:
            logger.error("Agent %d is not active", agent_id)
            raise ValueError(f"Agent {agent_id} is not active")

        if agent.provider != "bedrock":
            logger.error(
                "Agent %d has unsupported provider: %s", agent_id, agent.provider
            )
            raise ValueError("Only Bedrock provider is currently supported")

        # Calculate time window
        time_threshold = timezone.now() - timedelta(minutes=time_window_minutes)
        logger.debug("Using time threshold: %s", time_threshold)

        # Get recent news items from the stream's media sources
        news_items = News.objects.filter(
            source__in=stream.media.sources.all(), created_at__gte=time_threshold
        ).order_by("-created_at")[:max_items]

        if not news_items:
            logger.info(
                "No news items found in the last %d minutes", time_window_minutes
            )
            return {
                "processed": 0,
                "saved": 0,
                "error": None,
                "bedrock_response": {"full_response": None, "message_history": []},
            }

        logger.info("Found %d news items to process", len(news_items))

        # Get examples for the media
        examples = Examples.objects.filter(media=stream.media)
        examples_text = "\n\n".join(example.text for example in examples)
        logger.debug("Using %d examples for media", len(examples))

        # Join all news items together
        news_content = "\n\n---\n\n".join(
            f"Title: {news.title}\n\nContent: {news.text}\n\nURL: {news.link}"
            for news in news_items
        )
        logger.debug("Prepared news content with %d characters", len(news_content))

        # Format the prompts with variables
        now = timezone.now().strftime("%Y-%m-%d %H:%M:%S")

        # Prepare variables for template formatting
        template_vars = {
            "news": news_content,
            "examples": examples_text,
            "example": examples_text,  # Add backward compatibility for 'example'
            "now": now,
        }

        # Validate templates before formatting
        logger.debug(
            "Validating prompt templates with available variables: %s",
            list(template_vars.keys()),
        )

        system_missing_vars = validate_prompt_template(
            agent.system_prompt, template_vars
        )
        if system_missing_vars:
            error_msg = f"System prompt template contains undefined variables: {system_missing_vars}"  # noqa: E501
            logger.error(error_msg)
            raise ValueError(error_msg)

        user_missing_vars = validate_prompt_template(
            agent.user_prompt_template, template_vars
        )
        if user_missing_vars:
            error_msg = f"User prompt template contains undefined variables: {user_missing_vars}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Format prompts with validated templates
        try:
            system_prompt = agent.system_prompt.format(**template_vars)
            user_prompt = agent.user_prompt_template.format(**template_vars)

            logger.debug(
                "Successfully formatted prompts - System prompt length: %d, User prompt length: %d",
                len(system_prompt),
                len(user_prompt),
            )

        except Exception as e:
            error_msg = f"Failed to format prompt templates: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Initialize Bedrock client and make the API call
        try:
            bedrock_client = get_bedrock_client()
            logger.info("Successfully initialized Bedrock client")
        except Exception as e:
            error_msg = f"Failed to initialize Bedrock client: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info("Making API call to Bedrock")

        response = invoke_bedrock_anthropic(
            system_prompt=system_prompt, user_prompt=user_prompt, client=bedrock_client
        )

        processed_text = response.get("completion", "").strip()
        processed_count = len(news_items)
        saved_count = 0

        logger.info(
            "Received response from Bedrock with %d characters", len(processed_text)
        )

        # Parse the response and save to docs
        if save_to_docs and processed_text:
            try:
                # Parse the JSON response
                logger.debug("Attempting to parse JSON response: %s", processed_text)
                result = json.loads(processed_text)
                logger.info(
                    "Successfully parsed JSON response with schema: %s",
                    json.dumps({k: type(v).__name__ for k, v in result.items()}),
                )

                # Create a doc for each post
                posts = result.get("posts", [])
                logger.info("Processing %d posts from response", len(posts))

                for i, post in enumerate(posts, 1):
                    logger.debug("Creating doc for post %d/%d", i, len(posts))
                    doc = Doc.objects.create(
                        media=stream.media,
                        link=post.get("url", ""),
                        title=result.get("topic", "Untitled"),
                        text=post.get("text", ""),
                        status="new",
                    )
                    saved_count += 1
                    logger.info("Created doc %d for post %d/%d", doc.id, i, len(posts))

            except json.JSONDecodeError as e:
                error_msg = f"Failed to parse JSON response: {e}"
                logger.error("%s\nResponse text: %s", error_msg, processed_text)
                return {
                    "processed": processed_count,
                    "saved": 0,
                    "error": error_msg,
                    "response_text": processed_text,
                    "bedrock_response": {
                        "full_response": response.get("full_response"),
                        "message_history": response.get("message_history", []),
                    },
                }

        logger.info(
            "Completed processing with %d items processed and %d docs saved",
            processed_count,
            saved_count,
        )
        return {
            "processed": processed_count,
            "saved": saved_count,
            "error": None,
            "bedrock_response": {
                "full_response": response.get("full_response"),
                "message_history": response.get("message_history", []),
            },
        }

    except Exception as e:
        error_msg = f"Error in news stream task: {str(e)}"
        logger.error(error_msg, exc_info=True)  # Include full traceback
        return {
            "processed": 0,
            "saved": 0,
            "error": error_msg,
            "bedrock_response": {
                "full_response": (
                    response.get("full_response") if "response" in locals() else None
                ),
                "message_history": (
                    response.get("message_history", [])
                    if "response" in locals()
                    else []
                ),
            },
        }
