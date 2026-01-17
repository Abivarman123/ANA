"""Memory management tools for retrieving user memories from mem0."""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from livekit.agents import AgentSession, ChatContext, function_tool
from mem0 import AsyncMemoryClient

# Configure logging
logger = logging.getLogger(__name__)

# Constants
CACHE_FILE = ".memory_cache.json"
DEFAULT_USER = "abivarman"
MEMORY_FILTER_PROMPT = """Extract ONLY long-term, meaningful information. Be highly selective.

EXTRACT:
1. Personal Identity: Name, pronouns, location/timezone, persistent preferences
2. Long-term Goals: Projects lasting >30 days, career goals, learning objectives
3. Skills & Expertise: Professional role, technical skills, domains of expertise
4. Important Relationships: Key people relevant to tasks (teammates, collaborators)
5. Hard Constraints: Accessibility needs, permanent limitations, critical do/don'ts

STRICT EXCLUSIONS - DO NOT STORE:
- Temporary status: "I'm going to eat", "I'm back", "feeling tired"
- Simple confirmations: "yes", "ok", "can you hear me", "thanks"
- Routine commands: "open YouTube", "search for X", "create a file", "play music"
- Tool usage: Any request to use tools, search, or perform actions
- System checks: Testing functionality, checking if agent works
- Casual chat: Greetings, small talk, weather comments
- One-off tasks: Single-use information, temporary codes, short-term reminders
- Sensitive data: Phone numbers, addresses, passwords, API keys, financial info

RULES:
- Only store facts useful for >30 days
- Merge similar memories instead of duplicating
- Respect "don't remember this" requests
"""


def _get_mem0_client() -> Optional[AsyncMemoryClient]:
    """Get Mem0 client instance if API key is configured."""
    api_key = os.getenv("MEM0_API_KEY")
    if not api_key:
        return None
    return AsyncMemoryClient(api_key=api_key)


def _load_cache() -> Optional[Dict[str, Any]]:
    """Load memory cache from file."""
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load memory cache: {e}")
        return None


def _save_cache(data: Dict[str, Any]) -> None:
    """Save memory data to cache file."""
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to save memory cache: {e}")


def _format_memory_entry(result: Dict[str, Any], idx: int) -> str:
    """Format a single memory result."""
    memory_text = result.get("memory", result.get("text", ""))
    entry_parts = [f"{idx}. {memory_text}"]

    if categories := result.get("categories"):
        entry_parts.append(f"[Categories: {', '.join(categories)}]")

    if updated := result.get("updated_at"):
        # Keep only the date part YYYY-MM-DD
        entry_parts.append(f"(Updated: {updated[:10]})")

    return " ".join(entry_parts)


def _simplify_memories(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Simplify memory objects for context window and caching."""
    return [
        {
            "memory": r.get("memory", r.get("text", "")),
            "updated_at": r.get("updated_at", ""),
        }
        for r in results
    ]


def _format_memory_results(results: List[Dict[str, Any]]) -> str:
    """Format a list of memory results into a readable string."""
    if not results:
        return ""
    return "\n".join(_format_memory_entry(r, i) for i, r in enumerate(results, 1))


@function_tool()
async def search_memories(query: str, limit: int = 5) -> str:
    """Search for relevant memories from past conversations."""
    logger.info(f"Searching memories: '{query}' (limit: {limit})")

    client = _get_mem0_client()
    if not client:
        return "Memory system is not available. MEM0_API_KEY not configured."

    try:
        # Cap limit to reasonable size
        search_limit = min(limit, 20)
        response = await client.search(
            query=query, filters={"user_id": DEFAULT_USER}, limit=search_limit
        )

        results = response.get("results", []) if response else []

        if not results:
            return f"No relevant memories found for query: {query}"

        formatted_memories = _format_memory_results(results)
        logger.info(f"Found {len(results)} relevant memories")
        return f"Found {len(results)} relevant memories:\n\n{formatted_memories}"

    except Exception as e:
        logger.error(f"Error searching memories: {e}")
        return f"Failed to search memories: {str(e)}"


@function_tool()
async def get_recent_memories(count: int = 10) -> str:
    """Retrieve the most recent memories about the user."""
    logger.info(f"Retrieving {count} recent memories")

    client = _get_mem0_client()
    if not client:
        return "Memory system is not available. MEM0_API_KEY not configured."

    try:
        page_size = min(count, 20)
        response = await client.get_all(
            filters={"user_id": DEFAULT_USER}, page=1, page_size=page_size
        )

        # Handle simplified response handling (dict or list)
        results = (
            response.get("results", [])
            if isinstance(response, dict)
            else (response if isinstance(response, list) else [])
        )

        if not results:
            return "No recent memories found."

        formatted_memories = _format_memory_results(results)
        logger.info(f"Retrieved {len(results)} recent memories")
        return f"Retrieved {len(results)} recent memories:\n\n{formatted_memories}"

    except Exception as e:
        logger.error(f"Error retrieving recent memories: {e}")
        return f"Failed to retrieve recent memories: {str(e)}"


async def initialize_mem0_client() -> Optional[AsyncMemoryClient]:
    """Initialize Mem0 client and update custom instructions."""
    client = _get_mem0_client()
    if not client:
        logger.warning("MEM0_API_KEY not found. Memory features disabled.")
        return None

    logger.info("Initializing Mem0 client and updating instructions...")
    try:
        # Always update instructions to ensure they are current
        await client.project.update(custom_instructions=MEMORY_FILTER_PROMPT)
        logger.info("✓ Custom instructions updated successfully")
    except Exception as e:
        logger.error(f"Failed to update custom instructions: {e}")
        # Continue even if instruction update fails, as the client might still work

    return client


async def load_initial_memories(
    client: Optional[AsyncMemoryClient], user_name: str = DEFAULT_USER, count: int = 10
) -> Tuple[List[Dict[str, Any]], str]:
    """Load initial memories at startup, using cache if available."""
    if not client:
        return [], ""

    # Check cache first
    cache = _load_cache()
    if (
        cache
        and not cache.get("dirty")
        and cache.get("user_name") == user_name
        and cache.get("memories")
    ):
        logger.info("Using cached memories")
        memories = cache["memories"]
        return memories, json.dumps(memories)

    try:
        logger.info(f"Fetching recent memories for: {user_name}")
        response = await client.get_all(
            filters={"user_id": user_name}, page=1, page_size=count
        )

        results = (
            response.get("results", [])
            if isinstance(response, dict)
            else (response if isinstance(response, list) else [])
        )

        if results:
            # Simplify memory objects for caching
            memories = _simplify_memories(results)

            # Update cache
            _save_cache({"user_name": user_name, "memories": memories, "dirty": False})

            logger.info(f"Loaded {len(memories)} memories from API")
            return results, json.dumps(memories)

        logger.info("No existing memories found via API")
        return [], ""

    except Exception as e:
        logger.error(f"Failed to retrieve memories: {e}")
        return [], ""


async def setup_memory_system(
    user_name: str = DEFAULT_USER,
) -> Tuple[Optional[AsyncMemoryClient], ChatContext, str]:
    """
    Initialize the memory system, load initial memories, and create the starting context.

    Returns:
        Tuple containing:
        - mem0_client: The initialized client or None
        - initial_ctx: The chat context with memories loaded
        - memory_str: The string representation of memories (for filtering out of history)
    """
    client = await initialize_mem0_client()

    if client:
        results, memory_str = await load_initial_memories(client, user_name)
        ctx = create_memory_context(results, user_name, has_mem0=True)
        return client, ctx, memory_str

    # Fallback if no client or initialization failed
    return None, create_memory_context([], user_name, has_mem0=False), ""


def create_memory_context(
    results: List[Dict[str, Any]], user_name: str = DEFAULT_USER, has_mem0: bool = True
) -> ChatContext:
    """Create initial chat context with loaded memories."""
    initial_ctx = ChatContext()

    if results:
        # Simplify for context window
        memories = _simplify_memories(results)

        context_msg = (
            f"The user's name is {user_name}. "
            f"Here are the {len(memories)} most recent memories: {json.dumps(memories)}."
        )

        if has_mem0:
            context_msg += " Use search_memories() or get_recent_memories() tools to retrieve additional context when needed."

        initial_ctx.add_message(role="system", content=context_msg)

    return initial_ctx


async def save_conversation_to_mem0(
    session: AgentSession,
    client: Optional[AsyncMemoryClient],
    user_name: str = DEFAULT_USER,
    initial_memory_str: str = "",
) -> None:
    """Save conversation context to Mem0 on shutdown."""
    logger.info("=== Memory Shutdown Handler ===")

    if not client:
        logger.info("Mem0 client not available, skipping save")
        return

    if not session.history:
        logger.warning("No conversation history to save")
        return

    # Extract valid messages
    messages_to_save = []

    for item in session.history.items:
        if item.role not in ["user", "assistant"]:
            continue

        content_str = (
            "".join(item.content)
            if isinstance(item.content, list)
            else str(item.content)
        ).strip()

        # filters
        if not content_str:
            continue

        # Avoid re-saving the initial memory context prompt if it appears in history
        if initial_memory_str and initial_memory_str in content_str:
            continue

        messages_to_save.append({"role": item.role, "content": content_str})

    if not messages_to_save:
        logger.info("No eligible messages to save")
        return

    logger.info(f"Saving {len(messages_to_save)} messages to memory...")
    try:
        await client.add(messages_to_save, user_id=user_name)
        logger.info("✓ Chat context saved successfully")

        # Invalidate cache
        cache = _load_cache() or {}
        cache["dirty"] = True
        _save_cache(cache)

    except Exception as e:
        logger.error(f"Failed to save conversation: {e}")
