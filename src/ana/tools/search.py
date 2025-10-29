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
    
    DO NOT use this tool if the user wants to PLAY or WATCH a video/music.
    Use play_video or play_music tools instead for playback intent.

    Args:
        query: Can be a full URL (https://...), domain (youtube.com), or search query
        site: Optional - specify where to search (youtube, google, etc.) if query is a search term
    """
    query_lower = query.lower().strip()
    
    # Normalize common voice prefixes/suffixes
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
            
            # Build search URL based on site parameter (don't auto-detect)
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
    """Play a YouTube video directly - opens and auto-plays the video.
    
    Use this tool when user explicitly wants to PLAY, WATCH, or START a video.
    Examples: "play [video name]", "watch [video]", "start playing [video]"
    
    NOTE: For music/songs, use play_music tool instead.

    Args:
        query: Video name/search term OR direct YouTube URL
    """
    try:
        query_lower = query.lower()
        
        # Detect if this is actually a music request
        music_keywords = [
            "song", "music", "album", "artist", "track", "playlist"
        ]
        
        # If music intent detected, redirect to YouTube Music
        if any(keyword in query_lower for keyword in music_keywords):
            logging.info("Music intent detected in play_video, redirecting to YouTube Music")
            return await play_music(context, query)
        
        # If it's already a YouTube URL, use it directly
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
            video_id_match = re.search(r'"videoId":"([^\"]{11})"', html)

            if video_id_match:
                video_id = video_id_match.group(1)
                url = f"https://www.youtube.com/watch?v={video_id}"
                action = f"Playing '{query}'"
            else:
                # Fallback to search results if can't find video
                url = search_url
                action = f"Could not find video, showing search results for '{query}'"

        # Open in Chrome
        chrome_path = "C:/Program Files/Google/Chrome/Application/chrome.exe"
        subprocess.Popen([chrome_path, url])
        logging.info(f"Playing video: {url}")
        return f"✓ {action}"

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
        return f"⚠ Error occurred, opened YouTube search for '{query}'"


@function_tool()
@handle_tool_error("play_music")
async def play_music(
    context: RunContext,  # type: ignore
    query: str,
) -> str:
    """Play music on YouTube Music - opens and auto-plays the song/album/playlist.
    
    Use this tool when user wants to PLAY music/songs on YouTube Music.
    Examples: "play [song name]", "play music by [artist]", "play [playlist]"

    Args:
        query: Song/artist/album name OR direct YouTube Music URL
    """
    try:
        # If it's already a YouTube Music URL, use it directly
        if "music.youtube.com" in query:
            url = query if query.startswith("http") else f"https://{query}"
            action = "Playing music"
        else:
            # Search YouTube Music and get first result
            encoded_query = quote_plus(query)
            search_url = f"https://music.youtube.com/search?q={encoded_query}"

            # Fetch search results page
            async with aiohttp.ClientSession() as session:
                async with session.get(search_url) as response:
                    html = await response.text()

            # Extract first video ID from YouTube Music
            # YouTube Music uses different patterns, try multiple
            video_id_match = re.search(r'"videoId":"([^\"]{11})"', html)
            
            if video_id_match:
                video_id = video_id_match.group(1)
                url = f"https://music.youtube.com/watch?v={video_id}"
                action = f"Playing '{query}' on YouTube Music"
            else:
                # Fallback to search results if can't find song
                url = search_url
                action = f"Could not find song, showing YouTube Music search for '{query}'"

        # Open in Chrome
        chrome_path = "C:/Program Files/Google/Chrome/Application/chrome.exe"
        subprocess.Popen([chrome_path, url])
        logging.info(f"Playing music: {url}")
        return f"✓ {action}"

    except FileNotFoundError:
        # Fallback to default browser
        webbrowser.open(url)
        logging.info(f"Playing music in default browser: {url}")
        return f"✓ {action} in default browser"
    except Exception as e:
        logging.error(f"Error playing music: {e}")
        # Fallback to search results
        encoded_query = quote_plus(query)
        fallback_url = f"https://music.youtube.com/search?q={encoded_query}"
        webbrowser.open(fallback_url)
        return f"⚠ Error occurred, opened YouTube Music search for '{query}'"