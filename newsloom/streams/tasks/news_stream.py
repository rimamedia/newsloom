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
) -> Tuple[List[str], str]:
    """
    Validate prompt template and handle undefined variables by keeping them as text.

    Args:
        template: The prompt template string
        available_vars: Dictionary of available variables

    Returns:
        Tuple of (list of undefined variables, formatted template with undefined vars preserved)
    """
    undefined_vars = []
    formatted_template = template

    # Find all variables in the template using a basic format string pattern
    import re

    var_pattern = r"\{([^}]+)\}"
    template_vars = re.findall(var_pattern, template)

    # Check which variables are undefined
    for var in template_vars:
        if var not in available_vars:
            undefined_vars.append(var)
            # Replace undefined variable placeholder with escaped version
            formatted_template = formatted_template.replace(
                f"{{{var}}}", f"{{{{raw_{var}}}}}"
            )

    return undefined_vars, formatted_template


def invoke_bedrock_anthropic(
    system_prompt: str, user_prompt: str, stream=None, client=None
) -> Dict:
    """
    Invoke the Anthropic model through Amazon Bedrock with tool calling.

    Args:
        system_prompt: The system prompt that defines behavior
        user_prompt: The user prompt with content to process
        stream: Stream object for saving documents
        client: Optional pre-configured boto3 client

    Returns:
        Dict containing the model's response
    """
    try:
        if client is None:
            client = get_bedrock_client()

        # Define the create_documents tool
        tools = [
            {
                "name": "create_documents",
                "description": "Create a list of documents from the analyzed news content",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "topic": {
                            "type": "string",
                            "description": "The main topic or theme of the documents",
                        },
                        "documents": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "text": {
                                        "type": "string",
                                        "description": "The text content of the document",
                                    },
                                    "url": {
                                        "type": "string",
                                        "description": "The source URL for the document",
                                    },
                                },
                                "required": ["text", "url"],
                            },
                            "description": "Array of documents to create",
                        },
                    },
                    "required": ["topic", "documents"],
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
                    if content.get("name") == "create_documents":
                        tool_input = content.get("input", {})
                        logger.info(
                            "Successfully extracted tool input: %s",
                            json.dumps(tool_input, indent=2),
                        )

                        # Save documents to database
                        try:
                            documents = tool_input.get("documents", [])
                            topic = tool_input.get("topic", "Untitled")
                            saved_count = 0

                            if stream is None:
                                raise ValueError(
                                    "Stream object is required for saving documents"
                                )

                            for document in documents:
                                doc = Doc.objects.create(
                                    media=stream.media,
                                    link=document.get("url", ""),
                                    title=topic,
                                    text=document.get("text", ""),
                                    status="new",
                                )
                                saved_count += 1
                                logger.info("Created doc %d", doc.id)

                            result = {
                                "success": True,
                                "message": f"Successfully saved {saved_count} documents",
                                "saved_count": saved_count,
                            }
                        except Exception as e:
                            error_msg = f"Error saving documents: {str(e)}"
                            logger.error(error_msg)
                            result = {
                                "success": False,
                                "message": error_msg,
                                "saved_count": 0,
                            }

                        # Add tool result to messages
                        messages.append(
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "tool_result",
                                        "tool_use_id": content.get("id"),
                                        "content": json.dumps(result),
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
    **kwargs,  # Accept any additional configuration parameters
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
                "No relevant news items found in the last %d minutes for stream_id=%d. Skipping processing.",  # noqa: E501
                time_window_minutes,
                stream_id,
            )
            return {
                "processed": 0,
                "saved": 0,
                "error": f"None of the news items found in the last {time_window_minutes} minutes for stream_id={stream_id}",  # noqa: E501
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

        # Validate and format templates
        logger.debug(
            "Validating prompt templates with available variables: %s",
            list(template_vars.keys()),
        )

        system_undefined_vars, system_formatted = validate_prompt_template(
            agent.system_prompt, template_vars
        )
        if system_undefined_vars:
            logger.warning(
                "System prompt contains undefined variables that will be preserved as text: %s",
                system_undefined_vars,
            )

        user_undefined_vars, user_formatted = validate_prompt_template(
            agent.user_prompt_template, template_vars
        )
        if user_undefined_vars:
            logger.warning(
                "User prompt contains undefined variables that will be preserved as text: %s",
                user_undefined_vars,
            )

        # Add raw_ prefixed keys for undefined variables to preserve them in text
        format_vars = template_vars.copy()
        for var in system_undefined_vars + user_undefined_vars:
            format_vars[f"raw_{var}"] = f"{{{var}}}"

        # Format prompts with validated templates
        try:
            system_prompt = system_formatted.format(**format_vars)
            user_prompt = user_formatted.format(**format_vars)

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
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            stream=stream,
            client=bedrock_client,
        )

        processed_text = response.get("completion", "").strip()
        processed_count = len(news_items)

        # Calculate total saved documents from tool results
        saved_count = 0
        for message in response.get("message_history", []):
            if message.get("role") == "user" and message.get("content"):
                for content in message["content"]:
                    if content.get("type") == "tool_result":
                        try:
                            result = json.loads(content.get("content", "{}"))
                            saved_count += result.get("saved_count", 0)
                        except json.JSONDecodeError:
                            pass

        logger.info(
            "Received response from Bedrock with %d characters. Model output: %s",
            len(processed_text),
            (
                processed_text[:500] + "..."
                if len(processed_text) > 500
                else processed_text
            ),
        )

        logger.info(
            "Completed processing with %d items processed and %d docs saved. Final model response: %s",  # noqa: E501
            processed_count,
            saved_count,
            (
                processed_text[:500] + "..."
                if len(processed_text) > 500
                else processed_text
            ),
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
