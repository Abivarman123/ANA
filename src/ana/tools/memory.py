"""Memory management tools for retrieving user memories from mem0."""

import asyncio
import json
import logging
import os

from livekit.agents import AgentSession, ChatContext, function_tool
from mem0 import MemoryClient

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
- If unsure whether to store, DON'T store it
- Only store facts useful for >30 days
- Merge similar memories instead of duplicating
- Respect "don't remember this" requests
- Use concise third-person format with important details"""


def get_mem0_client():
    """Get or create mem0 client instance."""
    mem0_api_key = os.getenv("MEM0_API_KEY")
    if not mem0_api_key:
        return None
    return MemoryClient(api_key=mem0_api_key)


@function_tool()
async def search_memories(
    query: str,
    limit: int = 5,
) -> str:
    """
    Search for relevant memories from past conversations.
    Use this when you need additional context about the user that isn't in the current conversation.

    Args:
        query: The search query to find relevant memories (e.g., 'user preferences', 'past projects', 'skills')
        limit: Maximum number of memories to retrieve (default: 5, max: 20)

    Examples:
    - "What are the user's preferences for file organization?"
    - "What projects has the user worked on?"
    - "What are the user's skills and interests?"
    """
    mem0 = get_mem0_client()
    if not mem0:
        return "Memory system is not available. MEM0_API_KEY not configured."

    try:
        # Limit to max 20 to avoid overwhelming context
        limit = min(limit, 20)

        # Search memories for the user (run in executor to avoid blocking)
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            lambda: mem0.search(
                query=query, filters={"user_id": "abivarman"}, limit=limit
            ),
        )

        if not results or not results.get("results"):
            return f"No relevant memories found for query: {query}"

        # Format the results
        memories = []
        for idx, result in enumerate(results["results"], 1):
            memory_text = result.get("memory", "")
            categories = result.get("categories", [])
            updated_at = result.get("updated_at", "")

            memory_entry = f"{idx}. {memory_text}"
            if categories:
                memory_entry += f" [Categories: {', '.join(categories)}]"
            if updated_at:
                memory_entry += f" (Updated: {updated_at[:10]})"

            memories.append(memory_entry)

        return f"Found {len(memories)} relevant memories:\n\n" + "\n".join(memories)

    except Exception as e:
        logging.error(f"Error searching memories: {e}")
        return f"Failed to search memories: {str(e)}"


@function_tool()
async def get_recent_memories(
    count: int = 10,
) -> str:
    """
    Retrieve the most recent memories about the user.
    Use this to get a quick overview of recent interactions and information.

    Args:
        count: Number of recent memories to retrieve (default: 10, max: 20)
    """
    mem0 = get_mem0_client()
    if not mem0:
        return "Memory system is not available. MEM0_API_KEY not configured."

    try:
        # Limit to max 20
        count = min(count, 20)

        # Get recent memories (sorted by updated_at descending, run in executor)
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            lambda: mem0.get_all(
                filters={"user_id": "abivarman"}, page=1, page_size=count
            ),
        )

        if not results or not results.get("results"):
            return "No memories found."

        # Handle both dict and list responses
        if isinstance(results, dict):
            memory_list = results.get("results", [])
        elif isinstance(results, list):
            memory_list = results
        else:
            return "Unexpected response format from memory system."

        # Format the results
        memories = []
        for idx, result in enumerate(memory_list, 1):
            memory_text = result.get("memory", "")
            categories = result.get("categories", [])
            updated_at = result.get("updated_at", "")

            memory_entry = f"{idx}. {memory_text}"
            if categories:
                memory_entry += f" [Categories: {', '.join(categories)}]"
            if updated_at:
                memory_entry += f" (Updated: {updated_at[:10]})"

            memories.append(memory_entry)

        return f"Retrieved {len(memories)} recent memories:\n\n" + "\n".join(memories)

    except Exception as e:
        logging.error(f"Error retrieving recent memories: {e}")
        return f"Failed to retrieve recent memories: {str(e)}"


async def initialize_mem0_client():
    """Initialize Mem0 client with custom instructions.

    Returns:
        MemoryClient or None: Initialized client or None if API key not available
    """
    mem0_api_key = os.getenv("MEM0_API_KEY")
    if not mem0_api_key:
        return None

    mem0 = MemoryClient(api_key=mem0_api_key)

    # Configure custom instructions (skip verification for speed)
    # Run in executor to avoid blocking
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, lambda: mem0.project.update(custom_instructions=MEMORY_FILTER_PROMPT)
        )
    except Exception as e:
        logging.error(f"Failed to set custom instructions: {e}")

    return mem0


async def load_initial_memories(mem0, user_name: str = "abivarman", count: int = 5):
    """Load initial memories at startup.

    Args:
        mem0: MemoryClient instance
        user_name: User ID for memory retrieval
        count: Number of recent memories to load (default: 5, reduced for speed)

    Returns:
        tuple: (results list, memory_str for filtering)
    """
    try:
        if not mem0:
            return [], ""

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: mem0.get_all(
                filters={"user_id": user_name},
                page=1,
                page_size=count,
            ),
        )

        # Handle both list and dict responses
        if isinstance(response, dict):
            results = response.get("results", [])
        elif isinstance(response, list):
            results = response
        else:
            results = []

        # Create memory string for filtering
        if results:
            memories = [
                {"memory": result["memory"], "updated_at": result.get("updated_at", "")}
                for result in results
            ]
            memory_str = json.dumps(memories)
            return results, memory_str
        else:
            return [], ""

    except Exception as e:
        logging.error(f"Failed to retrieve memories: {e}")
        return [], ""


def create_memory_context(results, user_name: str = "abivarman", has_mem0: bool = True):
    """Create initial chat context with loaded memories.

    Args:
        results: List of memory results from Mem0
        user_name: User's name
        has_mem0: Whether Mem0 client is available

    Returns:
        ChatContext: Initial context with memory information
    """
    initial_ctx = ChatContext()

    if results:
        memories = [
            {"memory": result["memory"], "updated_at": result.get("updated_at", "")}
            for result in results
        ]

        # Inform the agent about available memories and tools
        memory_context = f"The user's name is {user_name}. Here are the {len(memories)} most recent memories about him: {json.dumps(memories)}."
        if has_mem0:
            memory_context += " Use search_memories() or get_recent_memories() tools to retrieve additional context when needed."

        initial_ctx.add_message(
            role="assistant",
            content=memory_context,
        )

    return initial_ctx


async def save_conversation_to_mem0(
    session: AgentSession, mem0, user_name: str = "abivarman", memory_str: str = ""
):
    """Save conversation context to Mem0 on shutdown (single batch operation).

    Args:
        session: AgentSession instance with conversation history
        mem0: MemoryClient instance
        user_name: User ID for memory storage
        memory_str: Initial memory string to filter out from saved messages
    """
    if not mem0 or not session.history:
        return

    messages_formatted = []

    for item in session.history.items:
        content_str = (
            "".join(item.content)
            if isinstance(item.content, list)
            else str(item.content)
        )

        # Skip messages that contain the initial memory context
        if memory_str and memory_str in content_str:
            continue

        # Skip empty messages (mem0 API rejects them)
        if not content_str or not content_str.strip():
            continue

        if item.role in ["user", "assistant"]:
            messages_formatted.append(
                {"role": item.role, "content": content_str.strip()}
            )

    if messages_formatted:
        try:
            # Single API call to save all conversation messages (run in executor)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, lambda: mem0.add(messages_formatted, user_id=user_name)
            )
        except Exception as e:
            logging.error(f"Failed to save conversation to mem0: {e}")
