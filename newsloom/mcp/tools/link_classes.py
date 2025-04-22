"""
MCP link_classes tool implementation for Newsloom.

This module provides MCP tool implementation for extracting CSS classes from links on a webpage.
"""

import json
import logging
from collections import Counter
from typing import Dict, List, Union

from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

# Import MCP types
try:
    from mcp.types import ErrorCode, McpError

    MCP_AVAILABLE = True
except ImportError:
    # Mock implementations for development without MCP SDK
    class ErrorCode:
        InvalidRequest = "InvalidRequest"
        MethodNotFound = "MethodNotFound"
        InvalidParams = "InvalidParams"
        InternalError = "InternalError"

    class McpError(Exception):
        def __init__(self, code, message):
            self.code = code
            self.message = message
            super().__init__(f"{code}: {message}")

    MCP_AVAILABLE = False

logger = logging.getLogger(__name__)

# Browser launch options optimized for container environment
BROWSER_OPTIONS = {
    "headless": True,
    "args": [
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--single-process",
    ],
}

# Context options optimized for memory usage
CONTEXT_OPTIONS = {
    "viewport": {"width": 1280, "height": 720},
    "java_script_enabled": True,
    "bypass_csp": False,
    "offline": False,
}


def register_link_classes_tools(server):
    """
    Register link_classes-related tools with the MCP server.

    Args:
        server: The MCP server instance
    """
    if not MCP_AVAILABLE:
        logger.warning("MCP SDK not available, registering mock link_classes tools")
        return

    @server.tool(
        name="get_link_classes",
        description="Get CSS classes from links on a webpage to help configure link selectors",
        input_schema={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL of the webpage to analyze",
                },
                "max_links": {
                    "type": "integer",
                    "description": "Maximum number of links to analyze (default 100)",
                    "minimum": 1,
                    "maximum": 1000,
                },
            },
            "required": ["url"],
        },
    )
    async def get_link_classes(request):
        """
        Get CSS classes from links on a webpage.

        Args:
            request: The MCP request object containing:
                url: URL of the webpage to analyze
                max_links: Maximum number of links to analyze (default 100)

        Returns:
            Dict with information about link classes and suggested selectors
        """
        try:
            args = request.params.arguments
            url = args.get("url")
            max_links = args.get("max_links", 100)

            # Call the implementation function
            result = _get_link_classes_impl(url, max_links)

            # Check for errors
            if result.get("error"):
                raise McpError(
                    ErrorCode.InternalError, f"Error analyzing page: {result['error']}"
                )

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, indent=2),
                    }
                ]
            }

        except McpError:
            # Re-raise MCP errors
            raise
        except Exception as e:
            logger.error(f"Error getting link classes: {str(e)}")
            raise McpError(
                ErrorCode.InternalError, f"Error getting link classes: {str(e)}"
            )


def _get_link_classes_impl(
    url: str, max_links: int = 100
) -> Dict[str, Union[List[str], str, int, None]]:
    """
    Extract CSS classes from links on a webpage.

    Args:
        url: URL of the webpage to analyze
        max_links: Maximum number of links to analyze (default 100)

    Returns:
        Dict with the following keys:
            common_classes: List of most common CSS classes with usage counts
            suggested_selectors: Ready-to-use CSS selectors based on common classes
            links_analyzed: Total number of links processed
            error: Any errors that occurred during analysis (None if successful)
    """
    try:
        class_stats = Counter()
        links_analyzed = 0
        result = {
            "common_classes": [],
            "suggested_selectors": "",
            "links_analyzed": 0,
            "error": None,
        }

        with sync_playwright() as p:
            browser = p.chromium.launch(**BROWSER_OPTIONS)
            try:
                context = browser.new_context(**CONTEXT_OPTIONS)
                try:
                    page = context.new_page()
                    try:
                        stealth_sync(page)
                        page.goto(url, timeout=30000)
                        page.wait_for_load_state("networkidle", timeout=30000)

                        # Get all links on the page
                        links = page.query_selector_all("a")

                        for link in links[:max_links]:
                            try:
                                # Get class attribute
                                class_attr = link.get_attribute("class")
                                if class_attr:
                                    # Split classes and add to counter
                                    classes = class_attr.split()
                                    class_stats.update(classes)
                                    links_analyzed += 1
                            except Exception as e:
                                logger.warning(f"Error processing link: {str(e)}")
                                continue

                        # Get most common classes with example links
                        common_classes = []
                        for cls, count in class_stats.most_common(10):
                            # Get example links for this class
                            example_links = []
                            for link in links[:max_links]:
                                try:
                                    class_attr = link.get_attribute("class")
                                    if class_attr and cls in class_attr.split():
                                        href = link.get_attribute("href") or ""
                                        text = link.inner_text() or ""
                                        example_links.append(
                                            f'<a href="{href}" class="{class_attr}">{text}</a>'
                                        )
                                        if (
                                            len(example_links) >= 2
                                        ):  # Get up to 2 examples
                                            break
                                except Exception as e:
                                    logger.warning(
                                        f"Error getting example link: {str(e)}"
                                    )
                                    continue

                            # Format class info with examples
                            class_info = f"{cls} (found in {count} links)"
                            if example_links:
                                class_info += "\nExample links:\n" + "\n".join(
                                    f"# {link}" for link in example_links
                                )
                            common_classes.append(class_info)

                        # Generate suggested selectors
                        if common_classes:
                            most_common = class_stats.most_common(1)[0][0]
                            result["suggested_selectors"] = f"a.{most_common}"

                            # If there are multiple common classes, suggest combinations
                            if len(class_stats) > 1:
                                second_most = class_stats.most_common(2)[1][0]
                                result[
                                    "suggested_selectors"
                                ] += f"\nOR\na.{most_common}.{second_most}"

                        result["common_classes"] = common_classes
                        result["links_analyzed"] = links_analyzed

                    finally:
                        if page:
                            page.close()
                finally:
                    if context:
                        context.close()
            finally:
                if browser:
                    browser.close()

        return result

    except Exception as e:
        logger.error(f"Error analyzing page: {str(e)}", exc_info=True)
        return {
            "common_classes": [],
            "suggested_selectors": "",
            "links_analyzed": 0,
            "error": str(e),
        }
