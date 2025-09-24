import asyncio
from typing import Dict, Any, List, Callable, Optional
import httpx
import logging

from src.services.langchain_agent_simple import LangChainAgent

logger = logging.getLogger(__name__)


class MCPAdapter:
    """Adapter to connect MCP tools to LangChain agent"""

    def __init__(self, mcp_server_url: str = "http://localhost:8000"):
        self.mcp_server_url = mcp_server_url
        self.agent = LangChainAgent()
        self.tool_mappings = {}

    async def load_mcp_tools(self):
        """Load available MCP tools from the server and register them with the agent"""
        mcp_tools = [
            {
                "name": "create_meeting_note",
                "description": "Create a new meeting note with title, participants, and optional agenda/notes",
                "func": self._create_async_tool_wrapper("create_meeting_note")
            },
            {
                "name": "create_backlog_item",
                "description": "Create a new backlog item with title, description, assignee, priority, tags, and due date",
                "func": self._create_async_tool_wrapper("create_backlog_item")
            },
            {
                "name": "update_backlog_status",
                "description": "Update the status of a backlog item (todo, in_progress, review, done, blocked, cancelled)",
                "func": self._create_async_tool_wrapper("update_backlog_status")
            },
            {
                "name": "search_backlogs",
                "description": "Search for backlog items using natural language query",
                "func": self._create_async_tool_wrapper("search_backlogs_by_query")
            },
            {
                "name": "get_overdue_tasks",
                "description": "Get all overdue backlog items that have passed their due date",
                "func": self._create_async_tool_wrapper("get_overdue_tasks")
            },
            {
                "name": "get_stale_tasks",
                "description": "Get backlog items that haven't been updated for specified number of days",
                "func": self._create_async_tool_wrapper("get_stale_tasks")
            }
        ]

        self.agent.register_mcp_tools(mcp_tools)
        self.agent.create_agent()
        logger.info(f"Loaded {len(mcp_tools)} MCP tools")

    def _create_async_tool_wrapper(self, tool_name: str) -> Callable:
        """Create an async wrapper for MCP tool calls"""
        async def tool_wrapper(**kwargs) -> str:
            try:
                return await self._call_mcp_tool(tool_name, kwargs)
            except Exception as e:
                logger.error(f"Error calling MCP tool {tool_name}: {e}")
                return f"Error: {str(e)}"

        def sync_wrapper(**kwargs) -> str:
            """Synchronous wrapper that runs the async function"""
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            return loop.run_until_complete(tool_wrapper(**kwargs))

        return sync_wrapper

    async def _call_mcp_tool(self, tool_name: str, params: Dict[str, Any]) -> str:
        """Call an MCP tool via HTTP request"""
        url = f"{self.mcp_server_url}/tools/{tool_name}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url,
                    json=params,
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()

                if result.get("success"):
                    return self._format_tool_result(tool_name, result)
                else:
                    return f"Tool execution failed: {result.get('error', 'Unknown error')}"

            except httpx.HTTPError as e:
                logger.error(f"HTTP error calling {tool_name}: {e}")
                return f"HTTP error: {str(e)}"
            except Exception as e:
                logger.error(f"Unexpected error calling {tool_name}: {e}")
                return f"Unexpected error: {str(e)}"

    def _format_tool_result(self, tool_name: str, result: Dict[str, Any]) -> str:
        """Format the tool result for the agent"""
        if tool_name == "create_meeting_note":
            return f"Created meeting '{result.get('meeting_id')}' at {result.get('file_path')}"

        elif tool_name == "create_backlog_item":
            return f"Created backlog item '{result.get('backlog_id')}' at {result.get('file_path')}"

        elif tool_name == "update_backlog_status":
            return f"Updated backlog item '{result.get('backlog_id')}' status to '{result.get('new_status')}'"

        elif tool_name == "search_backlogs_by_query":
            results = result.get('results', [])
            if not results:
                return "No matching backlog items found"

            formatted = "Found backlog items:\n"
            for item in results[:5]:
                formatted += f"- {item['id']}: {item.get('metadata', {}).get('title', 'Untitled')}\n"
            return formatted

        elif tool_name == "get_overdue_tasks":
            tasks = result.get('overdue_tasks', [])
            if not tasks:
                return "No overdue tasks"

            formatted = f"Found {result.get('count', 0)} overdue tasks:\n"
            for task in tasks[:5]:
                formatted += f"- {task['id']}: {task['title']} (due: {task['due_date']})\n"
            return formatted

        elif tool_name == "get_stale_tasks":
            tasks = result.get('stale_tasks', [])
            if not tasks:
                return f"No tasks stale for more than {result.get('threshold_days', 7)} days"

            formatted = f"Found {result.get('count', 0)} stale tasks:\n"
            for task in tasks[:5]:
                formatted += f"- {task['id']}: {task['title']} (last updated: {task['last_updated']})\n"
            return formatted

        else:
            return str(result)

    async def process_request(self, message: str, thread_id: str = "default") -> str:
        """Process a user request through the agent"""
        return await self.agent.process_message(message, thread_id)

    def stream_response(self, message: str, thread_id: str = "default"):
        """Stream the agent's response"""
        return self.agent.stream_response(message, thread_id)

    def get_conversation_history(self, thread_id: str = "default") -> List[Dict[str, Any]]:
        """Get conversation history for a thread"""
        return self.agent.get_conversation_history(thread_id)

    def clear_memory(self, thread_id: Optional[str] = None):
        """Clear conversation memory"""
        self.agent.clear_memory(thread_id)

    def get_available_tools(self) -> List[Dict[str, str]]:
        """Get list of available tools"""
        return self.agent.get_available_tools()