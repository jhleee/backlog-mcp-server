"""
MCP SSE Server Implementation using fastapi-mcp
Implements the Model Context Protocol with Server-Sent Events
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_mcp import FastApiMCP
from mcp.server import Server
from mcp.types import Tool, TextContent, CallToolResult
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import logging
from datetime import datetime
from typing import Any, Dict

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models import Meeting, Backlog, BacklogStatus
from src.services import GitService, VectorService, SchedulerService
from src.api.agent_endpoints import initialize_mcp_adapter

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize services
git_service = GitService()
vector_service = VectorService()
scheduler = SchedulerService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    # Startup
    scheduler.start()
    await initialize_mcp_adapter()
    logger.info("MCP SSE Server started")
    yield
    # Shutdown
    scheduler.stop()
    logger.info("MCP SSE Server shutdown")


# Create FastAPI app
app = FastAPI(
    title="Git-Chat-Log MCP SSE Server",
    description="MCP server with SSE support for Git-based meeting and backlog management",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize FastApiMCP
mcp = FastApiMCP(
    app,
    name="git-chat-log-mcp",
    description="MCP server for Git-based meeting and backlog management"
)


# Define MCP Tools
@mcp.server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available MCP tools"""
    return [
        Tool(
            name="create_meeting_note",
            description="Create a new meeting note and commit to Git",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Meeting title"},
                    "participants": {"type": "array", "items": {"type": "string"}, "description": "List of participants"},
                    "date": {"type": "string", "description": "Meeting date (ISO format)"},
                    "agenda": {"type": "string", "description": "Meeting agenda"},
                    "notes": {"type": "string", "description": "Meeting notes"}
                },
                "required": ["title", "participants"]
            }
        ),
        Tool(
            name="create_backlog_item",
            description="Create a new backlog item and commit to Git",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Backlog item title"},
                    "description": {"type": "string", "description": "Detailed description"},
                    "assignee": {"type": "string", "description": "Person assigned"},
                    "priority": {"type": "integer", "description": "Priority (1-5)"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags"},
                    "due_date": {"type": "string", "description": "Due date (ISO format)"}
                },
                "required": ["title", "description"]
            }
        ),
        Tool(
            name="update_backlog_status",
            description="Update the status of a backlog item",
            inputSchema={
                "type": "object",
                "properties": {
                    "item_id": {"type": "string", "description": "Backlog item ID"},
                    "status": {"type": "string", "description": "New status", "enum": ["todo", "in_progress", "review", "done", "blocked", "cancelled"]}
                },
                "required": ["item_id", "status"]
            }
        ),
        Tool(
            name="search_backlogs",
            description="Search for backlogs using natural language query",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "n_results": {"type": "integer", "description": "Number of results", "default": 5}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_overdue_tasks",
            description="Get all overdue backlog items",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_stale_tasks",
            description="Get backlog items not updated for specified days",
            inputSchema={
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "description": "Number of days", "default": 7}
                }
            }
        ),
        Tool(
            name="list_meetings",
            description="List all meeting notes",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="list_backlogs",
            description="List all backlog items",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]


@mcp.server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
    """Execute an MCP tool"""
    try:
        if name == "create_meeting_note":
            meeting_date = datetime.now()
            if arguments.get("date"):
                meeting_date = datetime.fromisoformat(arguments["date"])

            meeting = Meeting(
                id=datetime.now().strftime("%Y%m%d_%H%M%S"),
                title=arguments.get("title", "Untitled Meeting"),
                participants=arguments.get("participants", []),
                date=meeting_date,
                agenda=arguments.get("agenda"),
                notes=arguments.get("notes")
            )

            file_path = f"meetings/{meeting.get_filename()}"
            content = meeting.to_markdown()

            commit_sha = git_service.create_file(
                path=file_path,
                content=content,
                commit_message=f"Add meeting: {meeting.title}"
            )

            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"Created meeting '{meeting.title}' with ID {meeting.id} at {file_path}"
                )]
            )

        elif name == "create_backlog_item":
            due_date = None
            if arguments.get("due_date"):
                due_date = datetime.fromisoformat(arguments["due_date"])

            backlog = Backlog(
                title=arguments.get("title", "Untitled Task"),
                description=arguments.get("description", ""),
                assignee=arguments.get("assignee"),
                priority=arguments.get("priority", 3),
                tags=arguments.get("tags", []),
                due_date=due_date
            )

            file_path = f"backlogs/{backlog.get_filename()}"
            content = backlog.to_markdown()

            commit_sha = git_service.create_file(
                path=file_path,
                content=content,
                commit_message=f"Add backlog: {backlog.title}"
            )

            # Add to vector database
            vector_service.add_document(
                document_id=backlog.id,
                text=f"{backlog.title}\n{backlog.description}",
                metadata={
                    "type": "backlog",
                    "status": backlog.status.value,
                    "assignee": backlog.assignee,
                    "priority": backlog.priority,
                    "created_at": backlog.created_at.isoformat()
                }
            )

            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"Created backlog item '{backlog.title}' with ID {backlog.id}"
                )]
            )

        elif name == "update_backlog_status":
            item_id = arguments.get("item_id")
            new_status = arguments.get("status")

            file_path = f"backlogs/{item_id}.md"
            content = git_service.read_file(file_path)
            backlog = Backlog.from_markdown(content, item_id)

            backlog.status = BacklogStatus(new_status)
            backlog.updated_at = datetime.now()
            if new_status == "done":
                backlog.completed_at = datetime.now()

            updated_content = backlog.to_markdown()
            commit_sha = git_service.update_file(
                path=file_path,
                content=updated_content,
                commit_message=f"Update status of {backlog.title} to {new_status}"
            )

            # Update vector database
            vector_service.update_document(
                document_id=backlog.id,
                text=f"{backlog.title}\n{backlog.description}",
                metadata={
                    "type": "backlog",
                    "status": backlog.status.value,
                    "assignee": backlog.assignee,
                    "priority": backlog.priority,
                    "updated_at": backlog.updated_at.isoformat()
                }
            )

            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"Updated status of '{backlog.title}' to {new_status}"
                )]
            )

        elif name == "search_backlogs":
            query = arguments.get("query", "")
            n_results = arguments.get("n_results", 5)

            results = vector_service.search(
                query=query,
                n_results=n_results,
                filter={"type": "backlog"}
            )

            result_text = f"Found {results['count']} matching backlogs:\n"
            for item in results['results']:
                result_text += f"- {item['id']}: {item.get('metadata', {}).get('title', 'Untitled')}\n"

            return CallToolResult(
                content=[TextContent(type="text", text=result_text)]
            )

        elif name == "get_overdue_tasks":
            backlog_files = git_service.list_files("backlogs")
            overdue_tasks = []

            for file_name in backlog_files:
                content = git_service.read_file(f"backlogs/{file_name}")
                backlog = Backlog.from_markdown(content)

                if backlog.is_overdue():
                    overdue_tasks.append({
                        "id": backlog.id,
                        "title": backlog.title,
                        "assignee": backlog.assignee,
                        "due_date": backlog.due_date.isoformat() if backlog.due_date else None,
                        "status": backlog.status.value
                    })

            result_text = f"Found {len(overdue_tasks)} overdue tasks:\n"
            for task in overdue_tasks:
                result_text += f"- {task['title']} (ID: {task['id']}, Due: {task['due_date']})\n"

            return CallToolResult(
                content=[TextContent(type="text", text=result_text)]
            )

        elif name == "get_stale_tasks":
            days = arguments.get("days", 7)
            backlog_files = git_service.list_files("backlogs")
            stale_tasks = []

            for file_name in backlog_files:
                content = git_service.read_file(f"backlogs/{file_name}")
                backlog = Backlog.from_markdown(content)

                if backlog.is_stale(days):
                    stale_tasks.append({
                        "id": backlog.id,
                        "title": backlog.title,
                        "assignee": backlog.assignee,
                        "status": backlog.status.value,
                        "last_updated": backlog.updated_at.isoformat()
                    })

            result_text = f"Found {len(stale_tasks)} tasks not updated for {days} days:\n"
            for task in stale_tasks:
                result_text += f"- {task['title']} (Last updated: {task['last_updated']})\n"

            return CallToolResult(
                content=[TextContent(type="text", text=result_text)]
            )

        elif name == "list_meetings":
            meeting_files = git_service.list_files("meetings")
            meetings = []

            for file_name in meeting_files:
                content = git_service.read_file(f"meetings/{file_name}")
                meeting_id = file_name.replace(".md", "")
                meeting = Meeting.from_markdown(content, meeting_id)
                meetings.append({
                    "id": meeting.id,
                    "title": meeting.title,
                    "date": meeting.date.isoformat()
                })

            result_text = f"Found {len(meetings)} meetings:\n"
            for meeting in meetings:
                result_text += f"- {meeting['title']} ({meeting['date']})\n"

            return CallToolResult(
                content=[TextContent(type="text", text=result_text)]
            )

        elif name == "list_backlogs":
            backlog_files = git_service.list_files("backlogs")
            backlogs = []

            for file_name in backlog_files:
                content = git_service.read_file(f"backlogs/{file_name}")
                backlog = Backlog.from_markdown(content)
                backlogs.append({
                    "id": backlog.id,
                    "title": backlog.title,
                    "status": backlog.status.value,
                    "assignee": backlog.assignee
                })

            result_text = f"Found {len(backlogs)} backlog items:\n"
            for item in backlogs:
                result_text += f"- {item['title']} (Status: {item['status']}, Assignee: {item['assignee'] or 'None'})\n"

            return CallToolResult(
                content=[TextContent(type="text", text=result_text)]
            )

        else:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"Unknown tool: {name}"
                )],
                isError=True
            )

    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}")
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )],
            isError=True
        )


# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "protocol": "MCP-SSE"}


if __name__ == "__main__":
    import uvicorn
    import os

    host = os.getenv("HOST", "localhost")
    port = int(os.getenv("PORT", 8000))

    uvicorn.run(
        "src.mcp_sse_server:app",
        host=host,
        port=port,
        reload=True
    )