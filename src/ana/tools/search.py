"""Web search tools."""

import logging
import re
import subprocess
import webbrowser
from urllib.parse import quote_plus

import aiohttp
from langchain_community.tools import DuckDuckGoSearchRun
from livekit.agents import RunContext, function_tool

from .base import handle_tool_error


@function_tool()
@handle_tool_error("search_web")
async def search_web(
    context: RunContext,  # type: ignore
    query: str,
) -> str:
    """Search the web using DuckDuckGo."""
    results = DuckDuckGoSearchRun().run(tool_input=query)
    logging.info(f"Search results for '{query}': {results}")
    return results


@function_tool()
@handle_tool_error("open_search")
async def open_search(
    context: RunContext,  # type: ignore
    query: str,
    site: str = "",
) -> str:
    """Open Chrome with a URL, domain, or search query.

    Args:
        query: Can be a full URL (https://...), domain (youtube.com), or search query
        site: Optional - specify where to search (youtube, google, etc.) if query is a search term
    """
    query_lower = query.lower().strip()
    # Normalize common voice prefixes/suffixes like "open youtube"
    cleaned = re.sub(
        r"^(open|go to|goto|visit|launch|start|take me to)\s+", "", query_lower
    ).strip()
    cleaned = re.sub(r"\s+(website|site)$", "", cleaned).strip()

    # 1) Direct URL/domain handling using cleaned form
    if cleaned.startswith(("http://", "https://")):
        url = cleaned
        action = f"Opened {cleaned}"
    elif "." in cleaned and " " not in cleaned:
        url = (
            cleaned
            if cleaned.startswith(("http://", "https://"))
            else f"https://{cleaned}"
        )
        action = f"Opened {cleaned}"
    else:
        # 2) Common site aliases (exact match)
        site_aliases = {
            "youtube music": "https://music.youtube.com",
            "yt music": "https://music.youtube.com",
            "youtube": "https://www.youtube.com",
            "yt": "https://www.youtube.com",
            "google news": "https://news.google.com",
            "news": "https://news.google.com",
            "google": "https://www.google.com",
            "gmail": "https://mail.google.com",
            "amazon": "https://www.amazon.com",
            "reddit": "https://www.reddit.com",
            "github": "https://github.com",
            "twitter": "https://x.com",
            "x": "https://x.com",
        }
        if cleaned in site_aliases:
            url = site_aliases[cleaned]
            action = f"Opened {cleaned}"
        else:
            # 3) It's a search query - determine where to search
            encoded_query = quote_plus(query)
            site_lower = site.lower() if site else ""
            # Check if query itself indicates where to search
            if not site_lower:
                if any(word in query_lower for word in ["youtube", "video"]):
                    site_lower = "youtube"
                elif any(word in query_lower for word in ["reddit", "subreddit"]):
                    site_lower = "reddit"
                elif any(
                    word in query_lower for word in ["github", "repository", "repo"]
                ):
                    site_lower = "github"
            # Build search URL based on site
            if "youtube" in site_lower:
                url = f"https://www.youtube.com/results?search_query={encoded_query}"
            elif "amazon" in site_lower:
                url = f"https://www.amazon.com/s?k={encoded_query}"
            elif "wikipedia" in site_lower:
                url = f"https://en.wikipedia.org/wiki/Special:Search?search={encoded_query}"
            elif "reddit" in site_lower:
                url = f"https://www.reddit.com/search/?q={encoded_query}"
            elif "github" in site_lower:
                url = f"https://github.com/search?q={encoded_query}"
            else:  # Default to Google
                url = f"https://www.google.com/search?q={encoded_query}"
            action = f"Searched for '{query}' on {site_lower or 'Google'}"

    try:
        # Try to open in Chrome specifically on Windows
        chrome_path = "C:/Program Files/Google/Chrome/Application/chrome.exe"
        subprocess.Popen([chrome_path, url])
        logging.info(f"Opened Chrome: {url}")
        return f"✓ {action} in Chrome"
    except FileNotFoundError:
        # Fallback to default browser if Chrome not found
        webbrowser.open(url)
        logging.info(f"Opened default browser: {url}")
        return f"✓ {action} in default browser"


@function_tool()
@handle_tool_error("play_video")
async def play_video(
    context: RunContext,  # type: ignore
    query: str,
) -> str:
    """Search for a video on YouTube and play the first result.

    Args:
        query: Video search query (e.g., "Python tutorial", "how to cook pasta")
    """
    try:
        # If it's already a YouTube URL, just play it
        if "youtube.com" in query or "youtu.be" in query:
            url = query if query.startswith("http") else f"https://{query}"
            action = "Playing video"
        else:
            # Search YouTube and get first video
            encoded_query = quote_plus(query)
            search_url = f"https://www.youtube.com/results?search_query={encoded_query}"

            # Fetch search results page
            async with aiohttp.ClientSession() as session:
                async with session.get(search_url) as response:
                    html = await response.text()

            # Extract first video ID using regex
            # YouTube embeds video data in the page as JSON
            video_id_match = re.search(r'"videoId":"([^"]{11})"', html)

            if video_id_match:
                video_id = video_id_match.group(1)
                url = f"https://www.youtube.com/watch?v={video_id}"
                action = f"Playing first result for '{query}'"
            else:
                # Fallback to search results if can't find video
                url = search_url
                action = f"Opened search results for '{query}'"

        # Open in Chrome
        chrome_path = "C:/Program Files/Google/Chrome/Application/chrome.exe"
        subprocess.Popen([chrome_path, url])
        logging.info(f"Playing video: {url}")
        return f"✓ {action} in Chrome"

    except FileNotFoundError:
        # Fallback to default browser
        webbrowser.open(url)
        logging.info(f"Playing video in default browser: {url}")
        return f"✓ {action} in default browser"
    except Exception as e:
        logging.error(f"Error playing video: {e}")
        # Fallback to search results
        encoded_query = quote_plus(query)
        fallback_url = f"https://www.youtube.com/results?search_query={encoded_query}"
        webbrowser.open(fallback_url)
        return f"✓ Opened YouTube search for '{query}'"
