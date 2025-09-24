"""
MCP (Model Context Protocol) Server Implementation for FastAPI
Based on the MCP specification for tool discovery and execution
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import logging
from datetime import datetime

from src.models import Meeting, Backlog, BacklogStatus
from src.services import GitService, VectorService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["MCP"])

git_service = GitService()
vector_service = VectorService()


# MCP Protocol Models
class MCPToolParameter(BaseModel):
    name: str
    type: str
    description: str
    required: bool = True


class MCPTool(BaseModel):
    name: str
    description: str
    parameters: List[MCPToolParameter]


class MCPServerInfo(BaseModel):
    protocol_version: str = "1.0"
    server_name: str = "git-chat-log-mcp"
    server_version: str = "0.1.0"
    capabilities: List[str] = ["tools", "resources"]


class MCPToolsResponse(BaseModel):
    tools: List[MCPTool]


class MCPToolCallRequest(BaseModel):
    tool: str
    arguments: Dict[str, Any]


class MCPToolCallResponse(BaseModel):
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None


# MCP Discovery Endpoints
@router.get("/", response_model=MCPServerInfo)
async def get_server_info():
    """Get MCP server information"""
    return MCPServerInfo()


@router.get("/tools", response_model=MCPToolsResponse)
async def list_tools():
    """List all available MCP tools"""
    tools = [
        MCPTool(
            name="create_meeting_note",
            description="Create a new meeting note and commit to Git",
            parameters=[
                MCPToolParameter(name="title", type="string", description="Meeting title"),
                MCPToolParameter(name="participants", type="array", description="List of participants"),
                MCPToolParameter(name="date", type="string", description="Meeting date (ISO format)", required=False),
                MCPToolParameter(name="agenda", type="string", description="Meeting agenda", required=False),
                MCPToolParameter(name="notes", type="string", description="Meeting notes", required=False),
            ]
        ),
        MCPTool(
            name="create_backlog_item",
            description="Create a new backlog item and commit to Git",
            parameters=[
                MCPToolParameter(name="title", type="string", description="Backlog item title"),
                MCPToolParameter(name="description", type="string", description="Detailed description"),
                MCPToolParameter(name="assignee", type="string", description="Person assigned", required=False),
                MCPToolParameter(name="priority", type="integer", description="Priority (1-5)", required=False),
                MCPToolParameter(name="tags", type="array", description="Tags for categorization", required=False),
                MCPToolParameter(name="due_date", type="string", description="Due date (ISO format)", required=False),
            ]
        ),
        MCPTool(
            name="update_backlog_status",
            description="Update the status of a backlog item",
            parameters=[
                MCPToolParameter(name="item_id", type="string", description="Backlog item ID"),
                MCPToolParameter(name="status", type="string", description="New status (todo/in_progress/review/done/blocked/cancelled)"),
            ]
        ),
        MCPTool(
            name="search_backlogs",
            description="Search for backlogs using natural language query",
            parameters=[
                MCPToolParameter(name="query", type="string", description="Search query"),
                MCPToolParameter(name="n_results", type="integer", description="Number of results", required=False),
            ]
        ),
        MCPTool(
            name="get_overdue_tasks",
            description="Get all overdue backlog items",
            parameters=[]
        ),
        MCPTool(
            name="get_stale_tasks",
            description="Get backlog items not updated for specified days",
            parameters=[
                MCPToolParameter(name="days", type="integer", description="Number of days", required=False),
            ]
        ),
        MCPTool(
            name="list_meetings",
            description="List all meeting notes",
            parameters=[]
        ),
        MCPTool(
            name="list_backlogs",
            description="List all backlog items",
            parameters=[]
        ),
    ]

    return MCPToolsResponse(tools=tools)


@router.post("/tools/call", response_model=MCPToolCallResponse)
async def call_tool(request: MCPToolCallRequest):
    """Execute an MCP tool"""
    try:
        tool_name = request.tool
        args = request.arguments

        # Tool implementations
        if tool_name == "create_meeting_note":
            meeting_date = datetime.now()
            if args.get("date"):
                meeting_date = datetime.fromisoformat(args["date"])

            meeting = Meeting(
                id=datetime.now().strftime("%Y%m%d_%H%M%S"),
                title=args.get("title", "Untitled Meeting"),
                participants=args.get("participants", []),
                date=meeting_date,
                agenda=args.get("agenda"),
                notes=args.get("notes")
            )

            file_path = f"meetings/{meeting.get_filename()}"
            content = meeting.to_markdown()

            commit_sha = git_service.create_file(
                path=file_path,
                content=content,
                commit_message=f"Add meeting: {meeting.title}"
            )

            return MCPToolCallResponse(
                success=True,
                result={
                    "meeting_id": meeting.id,
                    "file_path": file_path,
                    "commit_sha": commit_sha
                }
            )

        elif tool_name == "create_backlog_item":
            due_date = None
            if args.get("due_date"):
                due_date = datetime.fromisoformat(args["due_date"])

            backlog = Backlog(
                title=args.get("title", "Untitled Task"),
                description=args.get("description", ""),
                assignee=args.get("assignee"),
                priority=args.get("priority", 3),
                tags=args.get("tags", []),
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

            return MCPToolCallResponse(
                success=True,
                result={
                    "backlog_id": backlog.id,
                    "file_path": file_path,
                    "commit_sha": commit_sha
                }
            )

        elif tool_name == "update_backlog_status":
            item_id = args.get("item_id")
            new_status = args.get("status")

            if not item_id or not new_status:
                raise ValueError("item_id and status are required")

            file_path = f"backlogs/{item_id}.md"
            content = git_service.read_file(file_path)
            backlog = Backlog.from_markdown(content, item_id)

            try:
                backlog.status = BacklogStatus(new_status)
            except ValueError:
                raise ValueError(f"Invalid status: {new_status}")

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

            return MCPToolCallResponse(
                success=True,
                result={
                    "backlog_id": backlog.id,
                    "new_status": new_status,
                    "commit_sha": commit_sha
                }
            )

        elif tool_name == "search_backlogs":
            query = args.get("query", "")
            n_results = args.get("n_results", 5)

            results = vector_service.search(
                query=query,
                n_results=n_results,
                filter={"type": "backlog"}
            )

            return MCPToolCallResponse(
                success=True,
                result=results
            )

        elif tool_name == "get_overdue_tasks":
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

            return MCPToolCallResponse(
                success=True,
                result={"overdue_tasks": overdue_tasks, "count": len(overdue_tasks)}
            )

        elif tool_name == "get_stale_tasks":
            days = args.get("days", 7)
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

            return MCPToolCallResponse(
                success=True,
                result={"stale_tasks": stale_tasks, "count": len(stale_tasks), "days": days}
            )

        elif tool_name == "list_meetings":
            meeting_files = git_service.list_files("meetings")
            meetings = []

            for file_name in meeting_files:
                content = git_service.read_file(f"meetings/{file_name}")
                meeting_id = file_name.replace(".md", "")
                meeting = Meeting.from_markdown(content, meeting_id)

                meetings.append({
                    "id": meeting.id,
                    "title": meeting.title,
                    "date": meeting.date.isoformat(),
                    "participants": meeting.participants
                })

            return MCPToolCallResponse(
                success=True,
                result={"meetings": meetings, "count": len(meetings)}
            )

        elif tool_name == "list_backlogs":
            backlog_files = git_service.list_files("backlogs")
            backlogs = []

            for file_name in backlog_files:
                content = git_service.read_file(f"backlogs/{file_name}")
                backlog = Backlog.from_markdown(content)

                backlogs.append({
                    "id": backlog.id,
                    "title": backlog.title,
                    "status": backlog.status.value,
                    "assignee": backlog.assignee,
                    "priority": backlog.priority
                })

            return MCPToolCallResponse(
                success=True,
                result={"backlogs": backlogs, "count": len(backlogs)}
            )

        else:
            return MCPToolCallResponse(
                success=False,
                error=f"Unknown tool: {tool_name}"
            )

    except Exception as e:
        logger.error(f"Error executing tool {request.tool}: {e}")
        return MCPToolCallResponse(
            success=False,
            error=str(e)
        )