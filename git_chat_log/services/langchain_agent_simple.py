import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import Tool

from config.settings import settings

logger = logging.getLogger(__name__)


class LangChainAgent:
    """Simplified LangChain agent without deprecated features"""

    def __init__(self):
        self.llm = None
        self.tools = []
        self.conversation_history = []
        self._initialize_llm()

    def _initialize_llm(self):
        """Initialize the LLM based on available API keys"""
        if settings.openai_api_key:
            self.llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.7,
                api_key=settings.openai_api_key
            )
            logger.info("Using OpenAI LLM")
        elif settings.anthropic_api_key:
            self.llm = ChatAnthropic(
                model="claude-3-haiku-20240307",
                temperature=0.7,
                api_key=settings.anthropic_api_key
            )
            logger.info("Using Anthropic LLM")
        else:
            logger.warning("No API key configured for LLM")

    def register_mcp_tools(self, mcp_tools: List[Dict[str, Any]]):
        """Register MCP tools for use by the agent"""
        for tool_def in mcp_tools:
            tool = Tool(
                name=tool_def['name'],
                description=tool_def['description'],
                func=tool_def['func']
            )
            self.tools.append(tool)
            logger.info(f"Registered MCP tool: {tool_def['name']}")

    def create_agent(self):
        """Create the agent - simplified version"""
        if not self.llm:
            raise ValueError("LLM not initialized. Please configure API key.")

        logger.info(f"Agent ready with {len(self.tools)} tools")

    async def process_message(self, message: str, thread_id: str = "default") -> str:
        """Process a user message and return response"""
        if not self.llm:
            raise ValueError("LLM not initialized. Please configure API key.")

        try:
            # Add to conversation history
            self.conversation_history.append({"role": "human", "content": message})

            # Parse the message to check if it needs tool use
            response = await self._process_with_tools(message)

            # Add response to history
            self.conversation_history.append({"role": "assistant", "content": response})

            logger.info(f"Processed message in thread {thread_id}")
            return response

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return f"Error processing request: {str(e)}"

    async def _process_with_tools(self, message: str) -> str:
        """Process message with tool support"""
        # Check if message requires tool use
        tool_keywords = {
            "create meeting": "create_meeting_note",
            "new meeting": "create_meeting_note",
            "add meeting": "create_meeting_note",
            "create backlog": "create_backlog_item",
            "new backlog": "create_backlog_item",
            "add backlog": "create_backlog_item",
            "update status": "update_backlog_status",
            "change status": "update_backlog_status",
            "search backlog": "search_backlogs",
            "find backlog": "search_backlogs",
            "overdue": "get_overdue_tasks",
            "stale": "get_stale_tasks",
            "old tasks": "get_stale_tasks"
        }

        message_lower = message.lower()
        tool_to_use = None

        for keyword, tool_name in tool_keywords.items():
            if keyword in message_lower:
                tool_to_use = tool_name
                break

        if tool_to_use:
            # Find the tool
            tool = next((t for t in self.tools if t.name == tool_to_use), None)
            if tool:
                try:
                    # Extract parameters from message (simplified)
                    params = self._extract_params(message, tool_to_use)
                    result = tool.func(**params)
                    return f"Tool executed: {tool_to_use}\nResult: {result}"
                except Exception as e:
                    return f"Error executing tool {tool_to_use}: {str(e)}"

        # If no tool needed, just use LLM for response
        if self.llm:
            messages = [HumanMessage(content=message)]
            response = await self.llm.ainvoke(messages)
            return response.content
        else:
            return "No LLM configured. Please set up OpenAI or Anthropic API key."

    def _extract_params(self, message: str, tool_name: str) -> Dict[str, Any]:
        """Extract parameters from message for tool (simplified)"""
        params = {}

        if tool_name == "create_meeting_note":
            params["title"] = "Meeting " + datetime.now().strftime("%Y-%m-%d")
            params["participants"] = []
            params["notes"] = message

        elif tool_name == "create_backlog_item":
            params["title"] = message[:50]
            params["description"] = message

        elif tool_name == "search_backlogs":
            params["query"] = message

        elif tool_name == "get_stale_tasks":
            params["days"] = 7

        return params

    def stream_response(self, message: str, thread_id: str = "default"):
        """Stream the agent's response as it's generated"""
        if not self.llm:
            yield "No LLM configured"
            return

        try:
            # For simplicity, just yield the full response
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response = loop.run_until_complete(self.process_message(message, thread_id))
            yield response

        except Exception as e:
            logger.error(f"Error streaming response: {e}")
            yield f"Error: {str(e)}"

    def get_conversation_history(self, thread_id: str = "default") -> List[Dict[str, Any]]:
        """Get the conversation history for a specific thread"""
        return self.conversation_history.copy()

    def clear_memory(self, thread_id: Optional[str] = None):
        """Clear conversation memory"""
        self.conversation_history.clear()
        logger.info("Cleared conversation memory")

    def get_available_tools(self) -> List[Dict[str, str]]:
        """Get list of available tools"""
        return [
            {
                "name": tool.name,
                "description": tool.description
            }
            for tool in self.tools
        ]