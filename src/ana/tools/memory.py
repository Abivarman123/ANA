"""Memory management tools for retrieving user memories from mem0."""

import json
import logging
import os

from livekit.agents import AgentSession, ChatContext, function_tool
from mem0 import AsyncMemoryClient

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


def get_mem0_client():
    """Get or create mem0 client instance."""
    mem0_api_key = os.getenv("MEM0_API_KEY")
    return AsyncMemoryClient(api_key=mem0_api_key) if mem0_api_key else None


async def verify_custom_instructions(mem0) -> bool:
    """Verify that custom instructions are properly set."""
    if not mem0:
        return False

    try:
        project_info = await mem0.project.get(fields=["custom_instructions"])
        current_instructions = (
            project_info.get("custom_instructions", "") if project_info else ""
        )

        if not current_instructions:
            logging.warning("⚠ Custom instructions are empty")
            return False

        key_phrases = ["STRICT EXCLUSIONS", "DO NOT STORE", "routine commands"]
        if sum(1 for p in key_phrases if p in current_instructions) >= 2:
            logging.info(
                f"✓ Custom instructions verified ({len(current_instructions)} chars)"
            )
            return True

        logging.warning("⚠ Custom instructions may be outdated")
        return False
    except Exception as e:
        logging.error(f"Failed to verify custom instructions: {e}")
        return False


def format_memory_results(results):
    """Format memory results into readable strings."""
    memories = []
    for idx, result in enumerate(results, 1):
        entry = f"{idx}. {result.get('memory', '')}"
        if cats := result.get("categories"):
            entry += f" [Categories: {', '.join(cats)}]"
        if updated := result.get("updated_at"):
            entry += f" (Updated: {updated[:10]})"
        memories.append(entry)
    return memories


@function_tool()
async def search_memories(query: str, limit: int = 5) -> str:
    """Search for relevant memories from past conversations."""
    logging.info(f"Searching memories: {query}, limit: {limit}")

    mem0 = get_mem0_client()
    if not mem0:
        return "Memory system is not available. MEM0_API_KEY not configured."

    try:
        results = await mem0.search(
            query=query, filters={"user_id": "abivarman"}, limit=min(limit, 20)
        )

        if not results or not results.get("results"):
            return f"No relevant memories found for query: {query}"

        memories = format_memory_results(results["results"])
        logging.info(f"Retrieved {len(memories)} memories")
        return f"Found {len(memories)} relevant memories:\n\n" + "\n".join(memories)
    except Exception as e:
        logging.error(f"Error searching memories: {e}")
        return f"Failed to search memories: {str(e)}"


@function_tool()
async def get_recent_memories(count: int = 10) -> str:
    """Retrieve the most recent memories about the user."""
    logging.info(f"Retrieving {count} recent memories")

    mem0 = get_mem0_client()
    if not mem0:
        return "Memory system is not available. MEM0_API_KEY not configured."

    try:
        results = await mem0.get_all(
            filters={"user_id": "abivarman"}, page=1, page_size=min(count, 20)
        )
        memory_list = (
            results.get("results", [])
            if isinstance(results, dict)
            else (results if isinstance(results, list) else [])
        )

        if not memory_list:
            return "No recent memories found."

        memories = format_memory_results(memory_list)
        logging.info(f"Retrieved {len(memories)} recent memories")
        return f"Retrieved {len(memories)} recent memories:\n\n" + "\n".join(memories)
    except Exception as e:
        logging.error(f"Error retrieving recent memories: {e}")
        return f"Failed to retrieve recent memories: {str(e)}"


async def initialize_mem0_client():
    """Initialize Mem0 client with custom instructions."""
    mem0_api_key = os.getenv("MEM0_API_KEY")
    if not mem0_api_key:
        logging.warning("MEM0_API_KEY not found. Memory features disabled.")
        return None

    logging.info("Initializing Mem0 client...")
    mem0 = AsyncMemoryClient(api_key=mem0_api_key)

    try:
        await mem0.project.update(custom_instructions=MEMORY_FILTER_PROMPT)
        logging.info("✓ Custom instructions updated")

        if not await verify_custom_instructions(mem0):
            logging.warning("⚠ Custom instructions verification failed")
    except Exception as e:
        logging.error(f"Failed to set custom instructions: {e}")

    logging.info(
        "Mem0 client initialized. Note: Instructions only apply to NEW memories"
    )
    return mem0


async def load_initial_memories(mem0, user_name: str = "abivarman", count: int = 10):
    """Load initial memories at startup."""
    if not mem0:
        return [], ""

    try:
        logging.info(f"Retrieving recent memories for: {user_name}")
        response = await mem0.get_all(filters={"user_id": user_name}, page=1, page_size=count)

        results = (
            response.get("results", [])
            if isinstance(response, dict)
            else (response if isinstance(response, list) else [])
        )

        if results:
            memories = [
                {"memory": r["memory"], "updated_at": r.get("updated_at", "")}
                for r in results
            ]
            logging.info(f"Loaded {len(memories)} memories at startup")
            return results, json.dumps(memories)

        logging.info("No existing memories found")
        return [], ""
    except Exception as e:
        logging.error(f"Failed to retrieve memories: {e}")
        return [], ""


def create_memory_context(results, user_name: str = "abivarman", has_mem0: bool = True):
    """Create initial chat context with loaded memories."""
    initial_ctx = ChatContext()

    if results:
        memories = [
            {"memory": r["memory"], "updated_at": r.get("updated_at", "")}
            for r in results
        ]
        memory_context = f"The user's name is {user_name}. Here are the {len(memories)} most recent memories: {json.dumps(memories)}."

        if has_mem0:
            memory_context += " Use search_memories() or get_recent_memories() tools to retrieve additional context when needed."

        initial_ctx.add_message(role="assistant", content=memory_context)

    return initial_ctx


async def save_conversation_to_mem0(
    session: AgentSession, mem0, user_name: str = "abivarman", memory_str: str = ""
):
    """Save conversation context to Mem0 on shutdown."""
    logging.info("=== Shutdown callback triggered ===")

    if not mem0:
        logging.info("Mem0 client not available, skipping memory save")
        return

    if not session.history:
        logging.warning("No conversation history to save")
        return

    messages_formatted = []
    for item in session.history.items:
        content_str = (
            "".join(item.content)
            if isinstance(item.content, list)
            else str(item.content)
        )

        if (memory_str and memory_str in content_str) or not content_str.strip():
            continue

        if item.role in ["user", "assistant"]:
            messages_formatted.append(
                {"role": item.role, "content": content_str.strip()}
            )

    if messages_formatted:
        logging.info(f"Saving {len(messages_formatted)} messages to memory")
        try:
            await mem0.add(messages_formatted, user_id=user_name)
            logging.info(f"✓ Chat context saved ({len(messages_formatted)} messages)")
        except Exception as e:
            logging.error(f"Failed to save conversation: {e}")
    else:
        logging.info("No messages to save to memory")
