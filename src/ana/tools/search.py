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
    context: RunContext,
    query: str,
) -> str:
    """Search the web using DuckDuckGo."""
    results = DuckDuckGoSearchRun().run(tool_input=query)
    logging.info(f"Search results for '{query}': {results}")
    return results


def _open_in_browser(url: str) -> str:
    """Helper to open URL in Chrome or fallback to default browser."""
    try:
        chrome_path = "C:/Program Files/Google/Chrome/Application/chrome.exe"
        subprocess.Popen([chrome_path, url])
        logging.info(f"Opened in Chrome: {url}")
        return "Chrome"
    except (FileNotFoundError, OSError):
        webbrowser.open(url)
        logging.info(f"Opened in default browser: {url}")
        return "default browser"


@function_tool()
@handle_tool_error("open_search")
async def open_search(
    context: RunContext,
    query: str,
    site: str = "",
) -> str:
    """Open Chrome with a URL, domain, or search query.

    DO NOT use this tool if the user wants to PLAY or WATCH a video/music.
    Use play_video or play_music tools instead for playback intent.

    Args:
        query: Can be a full URL (https://...), domain (youtube.com), or search query
        site: Optional - specify where to search (youtube, google, etc.) if query is a search term
    """
    # Clean common voice command patterns
    cleaned = re.sub(
        r"^(open|go to|goto|visit|launch|start|take me to)\s+", "", query.lower()
    ).strip()
    cleaned = re.sub(r"\s+(website|site)$", "", cleaned).strip()

    # Direct URL handling
    if cleaned.startswith(("http://", "https://")):
        url = cleaned
        action = f"Opened {cleaned}"
    # Direct domain handling (has dot, no spaces)
    elif "." in cleaned and " " not in cleaned:
        url = f"https://{cleaned}" if not cleaned.startswith("http") else cleaned
        action = f"Opened {cleaned}"
    else:
        # Check site aliases
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
            # Search query - route based on site parameter
            encoded_query = quote_plus(query)
            site_lower = site.lower() if site else ""

            search_urls = {
                "youtube": f"https://www.youtube.com/results?search_query={encoded_query}",
                "amazon": f"https://www.amazon.com/s?k={encoded_query}",
                "wikipedia": f"https://en.wikipedia.org/wiki/Special:Search?search={encoded_query}",
                "reddit": f"https://www.reddit.com/search/?q={encoded_query}",
                "github": f"https://github.com/search?q={encoded_query}",
            }

            # Find matching site or default to Google
            url = next(
                (url for key, url in search_urls.items() if key in site_lower),
                f"https://www.google.com/search?q={encoded_query}",
            )
            action = f"Searched for '{query}' on {site_lower or 'Google'}"

    browser = _open_in_browser(url)
    return f"✓ {action} in {browser}"


async def _get_first_youtube_video_id(
    query: str, use_music: bool = False
) -> tuple[str, str]:
    """
    Search YouTube/YouTube Music and return (url, action_message).
    Returns search results URL if video not found.
    """
    encoded_query = quote_plus(query)
    base_domain = "music.youtube.com" if use_music else "www.youtube.com"
    search_path = "search?q=" if use_music else "results?search_query="
    search_url = f"https://{base_domain}/{search_path}{encoded_query}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(search_url) as response:
                html = await response.text()

        # Extract first video ID
        video_id_match = re.search(r'"videoId":"([^"]{11})"', html)

        if video_id_match:
            video_id = video_id_match.group(1)
            watch_url = f"https://{base_domain}/watch?v={video_id}"
            platform = "YouTube Music" if use_music else "YouTube"
            return watch_url, f"Playing '{query}' on {platform}"
        else:
            platform = "YouTube Music" if use_music else "YouTube"
            return search_url, f"Showing {platform} search results for '{query}'"

    except Exception as e:
        logging.error(f"Error fetching YouTube: {e}")
        platform = "YouTube Music" if use_music else "YouTube"
        return search_url, f"Showing {platform} search results for '{query}'"


@function_tool()
@handle_tool_error("play_video")
async def play_video(
    context: RunContext,
    query: str,
) -> str:
    """Play a YouTube video directly - opens and auto-plays the video.

    Use this tool when user explicitly wants to PLAY, WATCH, or START a video.
    Examples: "play [video name]", "watch [video]", "start playing [video]"

    NOTE: For music/songs, use play_music tool instead.

    Args:
        query: Video name/search term OR direct YouTube URL
    """
    # Detect music intent and redirect
    music_keywords = ["song", "music", "album", "artist", "track", "playlist"]
    if any(keyword in query.lower() for keyword in music_keywords):
        logging.info("Music intent detected, redirecting to play_music")
        return await play_music(context, query)

    # Handle direct YouTube URLs
    if "youtube.com" in query or "youtu.be" in query:
        url = query if query.startswith("http") else f"https://{query}"
        action = "Playing video"
    else:
        # Search and get first video
        url, action = await _get_first_youtube_video_id(query, use_music=False)

    _open_in_browser(url)
    return f"✓ {action}"


@function_tool()
@handle_tool_error("play_music")
async def play_music(
    context: RunContext,
    query: str,
) -> str:
    """Play music on YouTube Music - opens and auto-plays the song/album/playlist.

    Use this tool when user wants to PLAY music/songs on YouTube Music.
    Examples: "play [song name]", "play music by [artist]", "play [playlist]"

    Args:
        query: Song/artist/album name OR direct YouTube Music URL
    """
    # Handle direct YouTube Music URLs
    if "music.youtube.com" in query:
        url = query if query.startswith("http") else f"https://{query}"
        action = "Playing music"
    else:
        # Search and get first song
        url, action = await _get_first_youtube_video_id(query, use_music=True)

    _open_in_browser(url)
    return f"✓ {action}"
