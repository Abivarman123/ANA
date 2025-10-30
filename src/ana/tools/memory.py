"""Memory management tools for retrieving user memories from mem0."""

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


def verify_custom_instructions(mem0) -> bool:
    """Verify that custom instructions are properly set.

    Args:
        mem0: MemoryClient instance

    Returns:
        True if instructions are set and match expected, False otherwise
    """
    if not mem0:
        return False

    try:
        project_info = mem0.project.get(fields=["custom_instructions"])
        if not project_info or "custom_instructions" not in project_info:
            logging.warning("⚠ No custom instructions found in project")
            return False

        current_instructions = project_info["custom_instructions"]
        if not current_instructions:
            logging.warning("⚠ Custom instructions are empty")
            return False

        # Check if our key phrases are present
        key_phrases = ["STRICT EXCLUSIONS", "DO NOT STORE", "routine commands"]
        matches = sum(1 for phrase in key_phrases if phrase in current_instructions)

        if matches >= 2:
            logging.info(
                f"✓ Custom instructions verified ({len(current_instructions)} chars)"
            )
            return True
        else:
            logging.warning("⚠ Custom instructions may be outdated or incorrect")
            logging.debug(
                f"Current instructions preview: {current_instructions[:200]}..."
            )
            return False

    except Exception as e:
        logging.error(f"Failed to verify custom instructions: {e}")
        return False


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
    logging.info(f"Searching memories with query: {query}, limit: {limit}")

    mem0 = get_mem0_client()
    if not mem0:
        return "Memory system is not available. MEM0_API_KEY not configured."

    try:
        # Limit to max 20 to avoid overwhelming context
        limit = min(limit, 20)

        # Search memories for the user
        results = mem0.search(
            query=query, filters={"user_id": "abivarman"}, limit=limit
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

        response = f"Found {len(memories)} relevant memories:\n\n" + "\n".join(memories)
        logging.info(f"Retrieved {len(memories)} memories for query: {query}")
        return response

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
    logging.info(f"Retrieving {count} recent memories")

    mem0 = get_mem0_client()
    if not mem0:
        return "Memory system is not available. MEM0_API_KEY not configured."

    try:
        # Limit to max 20
        count = min(count, 20)

        # Get recent memories (sorted by updated_at descending)
        results = mem0.get_all(
            filters={"user_id": "abivarman"}, page=1, page_size=count
        )

        # Handle both dict and list responses
        if isinstance(results, dict):
            memory_list = results.get("results", [])
        elif isinstance(results, list):
            memory_list = results
        else:
            return "Unexpected response format from memory system."

        if not memory_list:
            return "No recent memories found."

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

        response = f"Retrieved {len(memories)} recent memories:\n\n" + "\n".join(
            memories
        )
        logging.info(f"Retrieved {len(memories)} recent memories")
        return response

    except Exception as e:
        logging.error(f"Error retrieving recent memories: {e}")
        return f"Failed to retrieve recent memories: {str(e)}"


def initialize_mem0_client():
    """Initialize Mem0 client with custom instructions.

    Returns:
        MemoryClient or None: Initialized client or None if API key not available
    """
    mem0_api_key = os.getenv("MEM0_API_KEY")
    if not mem0_api_key:
        logging.warning(
            "MEM0_API_KEY not found in environment variables. Memory features will be disabled."
        )
        return None

    logging.info("Initializing Mem0 client...")
    mem0 = MemoryClient(api_key=mem0_api_key)

    # Configure custom instructions to filter what gets stored
    try:
        logging.info("Setting custom instructions for Mem0 project...")
        mem0.project.update(custom_instructions=MEMORY_FILTER_PROMPT)
        logging.info("✓ Custom instructions updated")

        # Verify the instructions were set correctly
        if not verify_custom_instructions(mem0):
            logging.warning(
                "⚠ Custom instructions verification failed - memories may not be filtered correctly"
            )
            logging.warning(
                "Consider checking your mem0 project settings at https://app.mem0.ai"
            )

    except Exception as e:
        logging.error(f"Failed to set custom instructions for Mem0: {e}")
        import traceback

        logging.error(traceback.format_exc())
        logging.error("⚠ Memories will be stored WITHOUT custom filtering!")

    logging.info("Mem0 client initialized successfully.")
    logging.info(
        "Note: Custom instructions only apply to NEW memories added after this point"
    )
    return mem0


def load_initial_memories(mem0, user_name: str = "abivarman", count: int = 10):
    """Load initial memories at startup.

    Args:
        mem0: MemoryClient instance
        user_name: User ID for memory retrieval
        count: Number of recent memories to load (default: 10)

    Returns:
        tuple: (results list, memory_str for filtering)
    """
    try:
        if not mem0:
            return [], ""

        logging.info(f"Retrieving recent memories for user: {user_name}")
        response = mem0.get_all(
            filters={"user_id": user_name},
            page=1,
            page_size=count,  # Only load specified number of memories at startup
        )
        logging.info(f"Mem0 response type: {type(response)}")

        # Handle both list and dict responses
        if isinstance(response, dict):
            results = response.get("results", [])
            total_count = response.get("count", len(results))
            logging.info(
                f"Loaded {len(results)} of {total_count} total memories at startup"
            )
        elif isinstance(response, list):
            results = response
            logging.info(f"Loaded {len(results)} memories at startup")
        else:
            logging.warning(f"Unexpected response type: {type(response)}")
            results = []

        # Create memory string for filtering
        if results:
            memories = [
                {"memory": result["memory"], "updated_at": result.get("updated_at", "")}
                for result in results
            ]
            memory_str = json.dumps(memories)
            logging.info(f"Retrieved {len(memories)} memories from Mem0 at startup.")
            return results, memory_str
        else:
            logging.info("No existing memories found.")
            return [], ""

    except Exception as e:
        logging.error(f"Failed to retrieve memories from Mem0: {e}")
        import traceback

        logging.error(traceback.format_exc())
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
    logging.info("=== Shutdown callback triggered ===")

    if not mem0:
        logging.info("Mem0 client not available, skipping memory save.")
        return

    logging.info("Shutting down, saving chat context to memory...")

    # Get conversation history from the session
    if not session.history:
        logging.warning("No conversation history available to save.")
        return

    messages_formatted = []
    logging.info(f"Session history items: {len(session.history.items)}")

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
        logging.info(f"Preparing to save {len(messages_formatted)} messages to memory")
        logging.debug(
            f"Messages preview: {messages_formatted[:2] if len(messages_formatted) > 2 else messages_formatted}"
        )

        try:
            # Single API call to save all conversation messages
            result = mem0.add(messages_formatted, user_id=user_name)
            logging.info(
                f"✓ Chat context saved to memory ({len(messages_formatted)} messages)"
            )
            logging.debug(f"Mem0 add result: {result}")
        except Exception as e:
            logging.error(f"Failed to save conversation to mem0: {e}")
            import traceback

            logging.error(traceback.format_exc())
    else:
        logging.info("No messages to save to memory")
