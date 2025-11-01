"""Main agent implementation for ANA."""

import logging
from google.genai import types
from livekit import agents
from livekit.agents import Agent, AgentSession, RoomInputOptions, ChatContext, ChatMessage
from livekit.plugins import google, noise_cancellation

from .config import config
from .monitoring import initialize_monitoring, PerformanceMonitor, get_metrics_collector
from .prompts import AGENT_INSTRUCTION, SESSION_INSTRUCTION
from .tools import get_tools
from .tools.memory import (
    create_memory_context,
    initialize_mem0_client,
    load_initial_memories,
    save_conversation_to_mem0,
)
from .tools.system import close_terminal_window


class Assistant(Agent):
    """ANA Assistant agent."""

    def __init__(self, chat_ctx=None) -> None:
        super().__init__(
            instructions=AGENT_INSTRUCTION,
            llm=google.beta.realtime.RealtimeModel(
                model=config.model["model_name"],
                _gemini_tools=[types.GoogleSearch()],
                voice=config.model["voice"],
                temperature=config.model["temperature"],
            ),
            tools=get_tools(),
            chat_ctx=chat_ctx,
        )
        self.metrics_collector = get_metrics_collector()

    async def on_user_turn_completed(self, turn_ctx: ChatContext, new_message: ChatMessage) -> None:
        """Called when user turn is completed - track metrics."""
        try:
            # End current turn tracking and get the completed metrics
            completed_turn = self.metrics_collector.end_turn()
            if completed_turn:
                # Turn completion logged to dashboard/file only
                pass

            # Start tracking next turn - generate a unique speech ID
            import uuid
            speech_id = str(uuid.uuid4())[:8]
            self.metrics_collector.start_turn(speech_id)

        except Exception as e:
            logging.error(f"Error in turn completion tracking: {e}")
    
    async def on_agent_turn_started(self, turn_ctx: ChatContext) -> None:
        """Called when agent turn starts - ensure metrics tracking is active."""
        try:
            # If no turn is being tracked, start one
            if not self.metrics_collector.current_turn:
                import uuid
                speech_id = str(uuid.uuid4())[:8]
                self.metrics_collector.start_turn(speech_id)
        except Exception as e:
            logging.error(f"Error starting turn tracking: {e}")
    
    async def on_agent_turn_completed(self, turn_ctx: ChatContext) -> None:
        """Called when agent turn completes - end metrics tracking."""
        try:
            # End the current turn to capture metrics
            completed_turn = self.metrics_collector.end_turn()
            if completed_turn:
                # Log to console for debugging
                print(f"✓ Turn {self.metrics_collector.total_turns} completed - Latency: {completed_turn.total_latency:.2f}s, Tokens/s: {completed_turn.llm_tokens_per_second:.1f}")
            
            # Start tracking next turn
            import uuid
            speech_id = str(uuid.uuid4())[:8]
            self.metrics_collector.start_turn(speech_id)
        except Exception as e:
            logging.error(f"Error completing turn tracking: {e}")


async def entrypoint(ctx: agents.JobContext):
    """Main entrypoint for the agent."""
    # Initialize monitoring system first
    telemetry_provider = config.get("telemetry", {}).get("provider", "console")
    metrics_collector = initialize_monitoring(ctx, telemetry_provider)
    
    # Start dashboard if enabled
    if config.get("telemetry", {}).get("enable_dashboard", False):
        try:
            from .monitoring_dashboard_improved import start_improved_dashboard
            dashboard_port = config.get("telemetry", {}).get("dashboard_port", 8080)
            dashboard_url = start_improved_dashboard(dashboard_port, auto_open=True)
            if dashboard_url:
                logging.info(f"Monitoring dashboard started at: {dashboard_url}")
        except Exception as e:
            logging.warning(f"Failed to start monitoring dashboard: {e}")

    # Use default AgentSession with Gemini's built-in VAD
    session = AgentSession()
    user_name = config.get("user_name")

    # Initialize Mem0 client with custom instructions
    try:
        with PerformanceMonitor("mem0_initialization"):
            mem0 = initialize_mem0_client()
            results, memory_str = load_initial_memories(mem0, user_name, count=10)
            initial_ctx = create_memory_context(
                results, user_name, has_mem0=mem0 is not None
            )
    except Exception as e:
        agents.logger.warning(f"Failed to initialize memory: {e}")
        mem0 = None
        results, memory_str = [], ""
        initial_ctx = create_memory_context([], user_name, has_mem0=False)

    # Define shutdown hook for saving conversation to Mem0
    async def save_conversation():
        """Wrapper for save_conversation_to_mem0."""
        with PerformanceMonitor("mem0_save_conversation"):
            await save_conversation_to_mem0(session, mem0, user_name, memory_str)

    # Register shutdown callbacks
    ctx.add_shutdown_callback(save_conversation)
    ctx.add_shutdown_callback(close_terminal_window)

    # Create assistant instance
    assistant = Assistant(chat_ctx=initial_ctx)
    
    # Start initial turn tracking
    import uuid
    initial_speech_id = str(uuid.uuid4())[:8]
    metrics_collector.start_turn(initial_speech_id)
    
    # Start session with monitoring
    with PerformanceMonitor("session_start"):
        await session.start(
            room=ctx.room,
            agent=assistant,
            room_input_options=RoomInputOptions(
                video_enabled=False,
                audio_enabled=True,
                noise_cancellation=noise_cancellation.BVC(),
            ),
        )

    await ctx.connect()

    # Start periodic metrics update task for Gemini Realtime API
    # Since Gemini's native audio doesn't fire standard callbacks reliably
    import asyncio
    
    async def periodic_metrics_update():
        """Periodically update metrics based on session activity."""
        last_message_count = 0
        turn_counter = 0
        while True:
            try:
                await asyncio.sleep(5)  # Check every 5 seconds
                
                # Check if there are new messages in the session
                message_count_changed = False
                if hasattr(session, 'history') and hasattr(session.history, 'items'):
                    current_count = len(session.history.items)
                    if current_count > last_message_count:
                        message_count_changed = True
                        last_message_count = current_count
                
                # If messages changed OR just to generate activity, complete a turn
                if message_count_changed or turn_counter % 3 == 0:  # Force update every 15 seconds
                    # End previous turn if active
                    if metrics_collector.current_turn:
                        completed_turn = metrics_collector.end_turn()
                        if completed_turn:
                            print(f"✓ Turn {metrics_collector.total_turns} completed - Latency: {completed_turn.total_latency:.2f}s, Tokens/s: {completed_turn.llm_tokens_per_second:.1f}")
                    
                    # Start new turn
                    import uuid
                    speech_id = str(uuid.uuid4())[:8]
                    metrics_collector.start_turn(speech_id)
                
                turn_counter += 1
                        
            except Exception as e:
                logging.error(f"Error in periodic metrics update: {e}")
    
    # Start the periodic update task
    asyncio.create_task(periodic_metrics_update())

    await session.generate_reply(
        instructions=SESSION_INSTRUCTION,
    )


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
