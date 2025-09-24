import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import Tool
from langchain.agents import initialize_agent, AgentType, AgentExecutor

from config.settings import settings

logger = logging.getLogger(__name__)


class LangChainAgent:
    def __init__(self):
        self.llm = None
        self.agent = None
        self.agent_executor = None
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
        """Create the LangChain agent with registered tools"""
        if not self.llm:
            raise ValueError("LLM not initialized. Please configure API key.")

        if not self.tools:
            logger.warning("No tools registered for agent")

        self.agent_executor = initialize_agent(
            tools=self.tools,
            llm=self.llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5
        )

        logger.info(f"Created agent with {len(self.tools)} tools")

    async def process_message(self, message: str, thread_id: str = "default") -> str:
        """Process a user message and return the agent's response"""
        if not self.agent_executor:
            raise ValueError("Agent not initialized. Call create_agent() first.")

        try:
            # Add to conversation history
            self.conversation_history.append({"role": "human", "content": message})

            result = await self.agent_executor.ainvoke(
                {"input": message}
            )

            response = result.get("output", "No response generated")

            # Add response to history
            self.conversation_history.append({"role": "assistant", "content": response})

            logger.info(f"Processed message in thread {thread_id}")
            return response

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return f"Error processing request: {str(e)}"

    def stream_response(self, message: str, thread_id: str = "default"):
        """Stream the agent's response as it's generated"""
        if not self.agent_executor:
            raise ValueError("Agent not initialized. Call create_agent() first.")

        try:
            result = self.agent_executor.invoke(
                {"input": message}
            )
            yield result.get("output", "")

        except Exception as e:
            logger.error(f"Error streaming response: {e}")
            yield f"Error: {str(e)}"

    def get_conversation_history(self, thread_id: str = "default") -> List[Dict[str, Any]]:
        """Get the conversation history for a specific thread"""
        try:
            return self.conversation_history.copy()

        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            return []

    def clear_memory(self, thread_id: Optional[str] = None):
        """Clear conversation memory for a specific thread or all threads"""
        try:
            self.conversation_history.clear()
            logger.info("Cleared conversation memory")

        except Exception as e:
            logger.error(f"Error clearing memory: {e}")

    def get_available_tools(self) -> List[Dict[str, str]]:
        """Get list of available tools"""
        return [
            {
                "name": tool.name,
                "description": tool.description
            }
            for tool in self.tools
        ]